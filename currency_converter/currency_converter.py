#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import with_statement, print_function, division

from collections import defaultdict, namedtuple
from datetime import datetime, timedelta, date as date_
import os.path as op
_DIRNAME = op.realpath(op.dirname(__file__))
from itertools import izip as zip
try:
    range = xrange
except NameError:
    pass
import six

Bounds = namedtuple('Bounds', 'first_date last_date')
CURRENCY_FILE = op.join(_DIRNAME, 'eurofxref-hist.csv')

__all__ = ['CurrencyConverter',
           'S3CurrencyConverter',
           'RateNotFoundError', ]


def _dates_between(first_date, last_date):
    """Yields all dates from first to last included."""
    for n in range(1 + (last_date - first_date).days):
        yield first_date + timedelta(days=n)


class RateNotFoundError(Exception):
    """Custom exception when data is missing in the rates file.

    With Python 2.6+ there no need to subclass __init__ and __str__.
    """
    pass


class CurrencyConverter(object):
    """
    At init, load the historic (since 1999) currencies from the ECB.

    Example:
    Date,USD,JPY,BGN,CYP,CZK,...
    2014-03-28,1.3759,140.9,1.9558,N/A,27.423,...
    2014-03-27,1.3758,...

    The main _rates structure is a dictionary with:
    + currencies as keys
    + {date: rate, ...} as values.

    bounds is a dict if first and last date available per currency.

    The rates are EUR foreign exchange reference rates.

    >>> from currency_converter import CurrencyConverter
    >>> c = CurrencyConverter()
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

        self.load_file(currency_file)

    def load_file(self, currency_file):
        """Load the currency file in the main structure."""
        with open(currency_file) as lines:
            self._load_lines(lines)

    def _load_lines(self, lines):
        self._rates = _rates = defaultdict(dict)
        na_values = self.na_values

        header = next(lines).strip().split(',')[1:]

        for line in lines:
            line = line.strip().split(',')
            # Fast parsing %Y-%m-%d format
            date = date_(int(line[0][:4]), int(line[0][5:7]), int(line[0][8:10]))

            for currency, rate in zip(header, line[1:]):
                if rate not in na_values and currency: # skip empty currency
                    _rates[currency][date] = float(rate)

        self.bounds = dict((currency, Bounds(min(r), max(r)))
                           for currency, r in six.iteritems(_rates))

        self.bounds[self.ref_currency] = Bounds(
            min(b.first_date for b in six.itervalues(self.bounds)),
            max(b.last_date for b in six.itervalues(self.bounds)))

        for currency in sorted(self._rates):
            self._set_missing_to_none(currency)
            if self.fallback_on_missing_rate:
                self._compute_missing_rates(currency)

        self.currencies = set(self._rates) | set([self.ref_currency])

    def _set_missing_to_none(self, currency):
        """Replace missing dates/rates with None inside date bounds for currency."""
        rates = self._rates[currency]
        first_date, last_date = self.bounds[currency]

        missing = 0
        for date in _dates_between(first_date, last_date):
            if date not in rates:
                rates[date] = None
                missing += 1

        if missing and self.verbose:
            print('{0}: {1} missing rates from {2} to {3}'.format(
                currency, missing, first_date, last_date))

    def _compute_missing_rates(self, currency):
        """Fill missing rates of a currency with the closest available ones."""
        rates = self._rates[currency]

        # tmp will store the closest rates forward and backward
        tmp = defaultdict(lambda: [None, None])
        for date, rate in sorted(six.iteritems(rates)):
            if rate is not None:
                closest_rate = rate
                dist = 0
            else:
                dist += 1
                tmp[date][0] = closest_rate, dist

        for date, rate in sorted(six.iteritems(rates), reverse=True):
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
                print(('{0}: filling {1} missing rate with {2} [dist:{3}] and '
                       '{4} [dist:{5}]').format(currency, date, r0, d0, r1, d1))


    def get_rate(self, currency='EUR', date=None):
        """Get a rate for a given currency and date.

        :type date: datetime.date

        >>> c.get_rate('USD', date=date(2014, 3, 28))
        1.375...
        >>> c.get_rate('AAA')
        Traceback (most recent call last):
        ValueError: AAA is not a supported currency
        >>> c.get_rate('BGN', date=date(2010, 11, 21)) # None, rate is missing
        """
        if currency == self.ref_currency:
            return 1.0

        if currency not in self._rates:
            raise ValueError("{0} is not a supported currency".format(currency))

        if date is None:
            date = self.bounds[currency].last_date

        try:
            date = date.date()
        except AttributeError:
            # This is just in case the input was a datetime and not a date
            pass

        if date not in self._rates[currency]:
            first_date, last_date = self.bounds[currency]
            if self.fallback_on_wrong_date:
                if self.verbose:
                    print(('{0} not in {1} bounds {2}/{3}, falling back to closest '
                           'one').format(date, currency, first_date, last_date))
                if date < first_date:
                    date = first_date
                elif date > last_date:
                    date = last_date
                else:
                    raise ValueError('Should never happen, bug in the code!')
            else:
                raise ValueError('{0} not in {1} bounds {2}/{3}'.format(
                    date, currency, first_date, last_date))

        return self._rates[currency][date]

    def convert(self, amount, currency, new_currency='EUR', date=None):
        """
        Return amount converted to a target currency.
        Target currency is EUR as default.
        Default date is most recent as default

        :type date: datetime.date

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
            raise ValueError("{0} is not a supported currency".format(currency))

        if date is None:
            date = self.bounds[currency].last_date

        r0 = self.get_rate(currency, date)
        r1 = self.get_rate(new_currency, date)

        if r0 is None:
            raise RateNotFoundError("{0} has no rate for {1}".format(currency, date))

        if r1 is None:
            raise RateNotFoundError("{0} has no rate for {1}".format(new_currency, date))

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


    def load_file(self, currency_file):
        lines = currency_file.get_contents_as_string().splitlines()
        self._load_lines(lines)


def main():
    import argparse
    from itertools import izip_longest

    def grouper(n, iterable, padvalue=None):
        """Grouper.

        >>> grouper(3, 'abcdefg', 'x')
        ('a','b','c'), ('d','e','f'), ('g','x','x')
        """
        return izip_longest(*[iter(iterable)] * n, fillvalue=padvalue)

    parser = argparse.ArgumentParser()
    parser.add_argument("amount", type=float)
    parser.add_argument("currency")

    parser.add_argument(
        "-t", "--to",
        help="Target currency, default is %(default)s",
        default='EUR')

    parser.add_argument(
        "-d", "--date",
        help="Date for conversion, with format %%Y-%%m-%%d",
        default=None)

    parser.add_argument(
        "-v", "--verbose",
        help="Display additional information on data set.",
        action='store_true')

    parser.add_argument(
        "-vv",
        help="Display details of missing rates completion.",
        action='store_true')

    parser.add_argument(
        "-f", "--file",
        help="Change currency file used, default %(default)s",
        default=CURRENCY_FILE)

    args = parser.parse_args()

    c = CurrencyConverter(currency_file=args.file,
                          fallback_on_wrong_date=True,
                          fallback_on_missing_rate=True,
                          verbose=args.vv)

    print('\nAvailable currencies [{0}]:'.format(len(c.currencies)))
    for tuple_ in grouper(10, sorted(c.currencies), padvalue=''):
        print(' '.join(tuple_))

    if args.verbose:
        print('\nCurrencies bounds:')
        for currency in sorted(c.currencies):
            if currency != c.ref_currency:
                print('{0}: from {1.first_date} to {1.last_date}'.format(
                    currency, c.bounds[currency]))

    if args.date is not None:
        date = datetime.strptime(args.date, '%Y-%m-%d').date()
    else:
        date = c.bounds[args.currency].last_date

    print()
    new_amount = c.convert(amount=args.amount,
                           currency=args.currency,
                           new_currency=args.to,
                           date=date)

    print('"{0:.3f} {1}" is "{2:.3f} {3}" on {4}.'.format(
        args.amount,
        args.currency,
        new_amount,
        args.to,
        date))


if __name__ == '__main__':
    main()
