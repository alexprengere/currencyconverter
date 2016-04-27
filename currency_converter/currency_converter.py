#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import with_statement, print_function, division

from collections import defaultdict
from datetime import datetime, timedelta
import os.path as op
from itertools import izip as zip
try:
    range = xrange
except NameError:
    pass
import six


__all__ = ['CurrencyConverter',
           'S3CurrencyConverter',
           'RateNotFoundError',
           'DATE_FORMAT',
           'NA',
           'REF_CURRENCY', ]

DEF_CURRENCY_FILE = op.join(op.realpath(op.dirname(__file__)), 'eurofxref-hist.csv')

# Reference currency
REF_CURRENCY = 'EUR'

# Date format in first column
DATE_FORMAT = "%Y-%m-%d"

# Missing values
NA = set(['', 'N/A'])


def dates_between(d0, d1):
    """Yields all dates from d0 to d1 included."""
    for n in range(1 + (d1 - d0).days):
        yield d0 + timedelta(days=n)


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

    The main structure is a dictionary with:
    + dates as keys
    + {'CUR': rate, ...} as values.

    The rates are EUR foreign exchange reference rates.

    >>> from currency_converter import CurrencyConverter
    >>> c = CurrencyConverter()
    """
    def __init__(self,
                 currency_file=DEF_CURRENCY_FILE,
                 fallback_on_wrong_date=False,
                 fallback_on_missing_rate=False,
                 verbose=False):

        # Global options
        self._fallback_on_wrong_date = fallback_on_wrong_date
        self._fallback_on_missing_rate = fallback_on_missing_rate
        self._verbose = verbose

        # Public members, which will be filled once the file is loaded
        self._rates = None
        self.currencies = None
        self.first_date = None
        self.last_date = None

        self.load_file(currency_file)


    def load_file(self, currency_file):
        """Load the currency file in the main structure."""
        with open(currency_file) as fl:
            self._load_file_like(fl)


    def _load_file_like(self, fl):
        self._rates = defaultdict(dict)
        header = next(fl).strip().split(',')[1:]

        for row in fl:
            row = row.strip().split(',')
            dt = datetime.strptime(row[0], DATE_FORMAT)

            for currency, rate in zip(header, row[1:]):
                if currency: # get rid of last empty currency in BCE data
                    self._rates[dt][currency] = None if rate in NA else float(rate)

        self.currencies = set([REF_CURRENCY] + [c for c in header if c])
        self.first_date = min(self._rates)
        self.last_date = max(self._rates)


    def _get_closest_valid_date(self, date):
        # Optimistically look for a date 4 days on either side
        for i in [ 1, -1, 2, -2, 3, -3, 4, -4, 5, -5 ]:
            d = date + timedelta(days=i)
            if d in self._rates:
                return d
        # Fall back on the slow linear scan over all dates
        return min((abs(date - d), d) for d in self._rates)[1]


    def _get_closest_available_date(self, currency, date):
        """Compute closest available date of a given date/currency.

        >>> from datetime import datetime
        >>> c._get_closest_available_date('BGN', datetime(1999, 12, 1))
        datetime.datetime(2000, 7, 19, 0, 0)
        """
        # Optimistically look for a date 4 days on either side
        for i in [ 1, -1, 2, -2, 3, -3, 4, -4 ]:
            d = date + timedelta(days=i)
            if d in self._rates and self._rates[d][currency] is not None:
                return d
        # Fall back on the slow linear scan over all dates
        return min((abs(date - d), d)
                   for d, r in six.iteritems(self._rates)
                   if r[currency] is not None)[1]


    def get_rate(self, currency='EUR', date=None):
        """Get a rate for a given currency and date.

        :type date: datetime

        >>> c.get_rate('USD', date=datetime(2014, 3, 28))
        1.375...
        >>> c.get_rate('AAA')
        Traceback (most recent call last):
        ValueError: Currency AAA not supported.
        >>> c.get_rate('BGN', date=datetime(1999, 11, 10)) # None, rate is missing
        """
        if date is None:
            date = self.last_date

        if date not in self._rates:
            if self._fallback_on_wrong_date:
                date = self._get_closest_valid_date(date)
                if self._verbose:
                    print('/!\\ Invalid date (currency was {0}), fallback to {1}'.format(
                            currency, date.strftime(DATE_FORMAT)))
            else:
                raise ValueError("Date {0} not supported.".format(date.strftime(DATE_FORMAT)))

        if currency == REF_CURRENCY:
            return 1.0

        if currency not in self._rates[date]:
            raise ValueError("Currency {0} not supported.".format(currency))

        if self._rates[date][currency] is None:
            if self._fallback_on_missing_rate:
                date = self._get_closest_available_date(currency, date)
                if self._verbose:
                    print('/!\\ Missing rate for {0}, fallback to {1}'.format(
                            currency, date.strftime(DATE_FORMAT)))
                return self._rates[date][currency]

        return self._rates[date][currency]


    def convert(self, amount, currency, new_currency='EUR', date=None):
        """
        Return amount converted to a target currency.
        Target currency is EUR as default.
        Default date is most recent as default

        :type date: datetime

        >>> c.convert(100, 'EUR', 'USD', date=datetime(2014, 3, 28))
        137.5...
        >>> c.convert(100, 'USD', date=datetime(2014, 3, 28))
        72.67...
        >>> c.convert(100, 'BGN', date=datetime(1999, 11, 10))
        Traceback (most recent call last):
        RateNotFoundError: Currency BGN has no rate for date 1999-11-10.
        """
        if date is None:
            date = self.last_date

        rate_0 = self.get_rate(currency, date)
        rate_1 = self.get_rate(new_currency, date)

        if rate_0 is None:
            raise RateNotFoundError("Currency {0} has no rate for date {1}.".format(
                                    currency, date.strftime(DATE_FORMAT)))

        if rate_1 is None:
            raise RateNotFoundError("Currency {0} has no rate for date {1}.".format(
                                    new_currency, date.strftime(DATE_FORMAT)))

        return float(amount) / rate_0 * rate_1


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
        self._load_file_like(lines)


def _test():
    """When called directly, launching doctests.
    """
    import doctest

    extraglobs = {
        'c': CurrencyConverter(),
    }

    opt = (doctest.ELLIPSIS |
           doctest.NORMALIZE_WHITESPACE |
           doctest.IGNORE_EXCEPTION_DETAIL)

    doctest.testmod(extraglobs=extraglobs, optionflags=opt)


def main():
    """Main.
    """
    import argparse
    from datetime import timedelta as td
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
        default=REF_CURRENCY)

    parser.add_argument(
        "-d", "--date",
        help="Date for conversion, with format {0}".format(
            DATE_FORMAT.replace('%', '%%')),
        default=None)

    parser.add_argument(
        "-v", "--verbose",
        help="Display additional information on data set.",
        action='store_true')

    parser.add_argument(
        "-f", "--file",
        help="Change currency file used, default %(default)s",
        default=DEF_CURRENCY_FILE)

    args = parser.parse_args()


    c = CurrencyConverter(currency_file=args.file,
                          fallback_on_wrong_date=True,
                          fallback_on_missing_rate=True,
                          verbose=True)

    print('Available currencies [{0}]:'.format(len(c.currencies)))
    for tuple_ in grouper(10, sorted(c.currencies), padvalue=''):
        print(' '.join(tuple_))

    print('\nAvailable dates: from {0} to {1}'.format(
        c.first_date.strftime(DATE_FORMAT), c.last_date.strftime(DATE_FORMAT)))

    if args.verbose:
        missing_dates = []
        for dt in dates_between(c.first_date, c.last_date):
            if dt not in c._rates:
                missing_dates.append(dt.strftime(DATE_FORMAT))

        if missing_dates:
            print('Missing [{0}/{1}]:'.format(
                len(missing_dates),
                (c.last_date - c.first_date).days + 1))
            for tuple_ in grouper(10, sorted(missing_dates), padvalue=''):
                print(' '.join(tuple_))

    if args.date is not None:
        dt = datetime.strptime(args.date, DATE_FORMAT)
    else:
        dt = c.last_date

    new_amount = c.convert(args.amount, args.currency, args.to, dt)

    print('\n"{0:.2f} {1}" is "{2:.2f} {3}" on {4}.'.format(
        args.amount,
        args.currency,
        new_amount,
        args.to,
        dt.strftime(DATE_FORMAT)))


if __name__ == '__main__':

    main()
