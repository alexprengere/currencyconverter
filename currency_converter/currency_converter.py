#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import with_statement, print_function, division

import sys
import os.path as op
from functools import wraps
import datetime
from datetime import timedelta
from collections import defaultdict, namedtuple

# We could have used "six", but like this we have no dependency
if sys.version_info[0] < 3:
    range = xrange
    from itertools import izip as zip, izip_longest as zip_longest

    def iteritems(d):
        return d.iteritems()
    def itervalues(d):
        return d.itervalues()
else:
    from itertools import zip_longest

    def iteritems(d):
        return d.items()
    def itervalues(d):
        return d.values()


_DIRNAME = op.realpath(op.dirname(__file__))
CURRENCY_FILE = op.join(_DIRNAME, 'eurofxref-hist.csv')

Bounds = namedtuple('Bounds', 'first_date last_date')

__all__ = ['CurrencyConverter',
           'S3CurrencyConverter',
           'RateNotFoundError', ]


def memoize(function):
    memo = {}
    @wraps(function)
    def wrapper(*args):
        if args not in memo:
            memo[args] = function(*args)
        return memo[args]
    return wrapper


@memoize
def list_dates_between(first_date, last_date):
    """Returns all dates from first to last included."""
    return [first_date + timedelta(days=n)
            for n in range(1 + (last_date - first_date).days)]


@memoize
def parse_date(s):
    """Fast %Y-%m-%d parsing."""
    return datetime.date(int(s[:4]), int(s[5:7]), int(s[8:10]))


class RateNotFoundError(Exception):
    """Custom exception when data is missing in the rates file."""
    pass


class CurrencyConverter(object):
    """
    At init, load the historic currencies (since 1999) from the ECB.
    The rates are EUR foreign exchange reference rates:

    Date,USD,JPY,BGN,CYP,CZK,...
    2014-03-28,1.3759,140.9,1.9558,N/A,27.423,...
    2014-03-27,1.3758,...

    ``_rates`` is a dictionary with:
    + currencies as keys
    + {date: rate, ...} as values.

    ``currencies`` is a set of all available currencies.
    ``bounds`` is a dict if first and last date available per currency.
    """
    def __init__(self,
                 currency_file=CURRENCY_FILE,
                 fallback_on_wrong_date=False,
                 fallback_on_missing_rate=False,
                 ref_currency='EUR',
                 na_values=frozenset(['', 'N/A']),
                 verbose=False):

        # Global options
        self.fallback_on_wrong_date = fallback_on_wrong_date
        self.fallback_on_missing_rate = fallback_on_missing_rate
        self.ref_currency = ref_currency # reference currency of rates
        self.na_values = na_values       # missing values
        self.verbose = verbose

        # Will be filled once the file is loaded
        self._rates = None
        self.bounds = None
        self.currencies = None

        if currency_file is not None:
            self._load_file(currency_file)

    def _load_file(self, currency_file):
        """To be subclassed if alternate methods of loading data."""
        with open(currency_file) as lines:
            self._load_lines(lines)

    def _load_lines(self, lines):
        _rates = self._rates = defaultdict(dict)
        na_values = self.na_values

        header = next(lines).strip().split(',')[1:]

        for line in lines:
            line = line.strip().split(',')
            date = parse_date(line[0])
            for currency, rate in zip(header, line[1:]):
                if rate not in na_values and currency: # skip empty currency
                    _rates[currency][date] = float(rate)

        self.currencies = set(self._rates) | set([self.ref_currency])
        self._compute_bounds()

        for currency in sorted(self._rates):
            self._set_missing_to_none(currency)
            if self.fallback_on_missing_rate:
                self._compute_missing_rates(currency)

    def _compute_bounds(self):
        self.bounds = dict((currency, Bounds(min(r), max(r)))
                           for currency, r in iteritems(self._rates))

        self.bounds[self.ref_currency] = Bounds(
            min(b.first_date for b in itervalues(self.bounds)),
            max(b.last_date for b in itervalues(self.bounds)))

    def _set_missing_to_none(self, currency):
        """Fill missing rates of a currency with the closest available ones."""
        rates = self._rates[currency]
        first_date, last_date = self.bounds[currency]

        for date in list_dates_between(first_date, last_date):
            if date not in rates:
                rates[date] = None

        if self.verbose:
            missing = len([r for r in itervalues(rates) if r is None])
            if missing:
                print('{0}: {1} missing rates from {2} to {3} ({4} days)'.format(
                    currency, missing, first_date, last_date,
                    1 + (last_date - first_date).days))

    def _compute_missing_rates(self, currency):
        """Fill missing rates of a currency with the closest available ones."""
        rates = self._rates[currency]

        # tmp will store the closest rates forward and backward
        tmp = defaultdict(lambda: [None, None])

        for date in sorted(rates):
            rate = rates[date]
            if rate is not None:
                closest_rate = rate
                dist = 0
            else:
                dist += 1
                tmp[date][0] = closest_rate, dist

        for date in sorted(rates, reverse=True):
            rate = rates[date]
            if rate is not None:
                closest_rate = rate
                dist = 0
            else:
                dist += 1
                tmp[date][1] = closest_rate, dist

        for date in sorted(tmp):
            (r0, d0), (r1, d1) = tmp[date]
            rates[date] = (r0 * d1 + r1 * d0) / (d0 + d1)
            if self.verbose:
                print(('{0}: filling {1} missing rate using {2} ({3}d old) and '
                       '{4} ({5}d later)').format(currency, date, r0, d0, r1, d1))

    def _get_rate(self, currency, date):
        """Get a rate for a given currency and date.

        :type date: datetime.date

        >>> from datetime import date
        >>> c = CurrencyConverter()
        >>> c._get_rate('USD', date=date(2014, 3, 28))
        1.375...
        >>> c._get_rate('BGN', date=date(2010, 11, 21))
        Traceback (most recent call last):
        RateNotFoundError: BGN has no rate for 2010-11-21
        """
        if currency == self.ref_currency:
            return 1.0

        if date not in self._rates[currency]:
            first_date, last_date = self.bounds[currency]

            if not self.fallback_on_wrong_date:
                raise RateNotFoundError('{0} not in {1} bounds {2}/{3}'.format(
                    date, currency, first_date, last_date))

            if date < first_date:
                fallback_date = first_date
            elif date > last_date:
                fallback_date = last_date
            else:
                raise AssertionError('Should never happen, bug in the code!')

            if self.verbose:
                print(r'/!\ {0} not in {1} bounds {2}/{3}, falling back to {4}'.format(
                    date, currency, first_date, last_date, fallback_date))

            date = fallback_date

        rate = self._rates[currency][date]
        if rate is None:
            raise RateNotFoundError('{0} has no rate for {1}'.format(currency, date))
        return rate

    def convert(self, amount, currency, new_currency='EUR', date=None):
        """Convert amount from a currency to another one.

        :type date: datetime.date

        >>> from datetime import date
        >>> c = CurrencyConverter()
        >>> c.convert(100, 'EUR', 'USD', date=date(2014, 3, 28))
        137.5...
        >>> c.convert(100, 'USD', date=date(2014, 3, 28))
        72.67...
        >>> c.convert(100, 'BGN', date=date(2010, 11, 21))
        Traceback (most recent call last):
        RateNotFoundError: BGN has no rate for 2010-11-21
        """
        # ref_currency is in self.currencies
        if currency not in self.currencies:
            raise ValueError('{0} is not a supported currency'.format(currency))

        if date is None:
            date = self.bounds[currency].last_date
        else:
            try:
                date = date.date() # Fallback if input was a datetime object
            except AttributeError:
                pass

        r0 = self._get_rate(currency, date)
        r1 = self._get_rate(new_currency, date)

        return float(amount) / r0 * r1


class S3CurrencyConverter(CurrencyConverter):
    """
    Load the ECB CSV file from an S3 key instead of from a local file.
    The first argument should be an instance of boto.s3.key.Key (or any other
    object that provides a get_contents_as_string() method which returns the
    CSV file as a string).
    """
    def __init__(self, currency_file, **kwargs):
        """Make currency_file a required attribute"""
        super(S3CurrencyConverter, self).__init__(currency_file, **kwargs)

    def _load_file(self, currency_file):
        lines = currency_file.get_contents_as_string().splitlines()
        self._load_lines(lines)


def grouper(iterable, n, fillvalue=None):
    """Group iterable by n elements.

    >>> grouper('abcdefg', 3, fillvalue='x')
    [('a', 'b', 'c'), ('d', 'e', 'f'), ('g', 'x', 'x')]
    """
    return list(zip_longest(*[iter(iterable)] * n, fillvalue=fillvalue))


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('amount', type=float)
    parser.add_argument('currency')

    parser.add_argument(
        '-t', '--to',
        help='target currency, default is %(default)s',
        default='EUR')

    parser.add_argument(
        '-d', '--date',
        help='date of rate, with format %%Y-%%m-%%d',
        default=None)

    parser.add_argument(
        '-v', '--verbose',
        help=('display available currencies, use twice (-vv) to '
              'also display details of missing rates completion'),
        action='count',
        default=0)

    parser.add_argument(
        '-f', '--file',
        help='change currency file used, default is %(default)s',
        default=CURRENCY_FILE)

    args = parser.parse_args()

    c = CurrencyConverter(currency_file=args.file,
                          fallback_on_wrong_date=True,
                          fallback_on_missing_rate=True,
                          verbose=args.verbose > 1)
    currencies = sorted(c.currencies)

    if args.verbose:
        print('{0} available currencies:'.format(len(currencies)))
        for group in grouper(currencies, 10, fillvalue=''):
            print(' '.join(group))
        print()

        currencies.sort(key=lambda u: c.bounds[u].last_date, reverse=True)
        currencies.sort(key=lambda u: c.bounds[u].first_date)
        for currency in currencies:
            first_date, last_date = c.bounds[currency]
            print('{0}: from {1} to {2} ({3} days)'.format(
                currency, first_date, last_date,
                1 + (last_date - first_date).days))
        print()

    if args.currency not in c.currencies:
        print(r'/!\ "{0}" is not in available currencies:'.format(args.currency))
        for group in grouper(currencies, 10, fillvalue=''):
            print(' '.join(group))
        exit(1)

    if args.date is not None:
        date = parse_date(args.date)
    else:
        date = c.bounds[args.currency].last_date

    new_amount = c.convert(amount=args.amount,
                           currency=args.currency,
                           new_currency=args.to,
                           date=date)

    print('{0:.3f} {1} = {2:.3f} {3} on {4}'.format(
        args.amount,
        args.currency,
        new_amount,
        args.to,
        date))


if __name__ == '__main__':
    main()
