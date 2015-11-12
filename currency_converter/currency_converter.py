#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import with_statement, print_function, division

from collections import defaultdict
from datetime import datetime
import os.path as op

import six


DEF_CURRENCY_FILE = op.join(op.realpath(op.dirname(__file__)), 'eurofxref-hist.csv')

# Reference currency
REF_CURRENCY = 'EUR'

# Date format in first column
DATE_FORMAT = "%Y-%m-%d"

# Field separator
DELIMITER = ","

# Missing values
NA_VALUES = set(['', 'N/A'])


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
                 currency_file=None,
                 fallback_on_wrong_date=False,
                 fallback_on_missing_rate=False,
                 verbose=False):

        # Global parameters
        self._fallback_on_wrong_date = fallback_on_wrong_date
        self._fallback_on_missing_rate = fallback_on_missing_rate
        self._verbose = verbose

        # Main structure
        self._rates = None

        # Public members, which will be filled once the file is loaded
        self.currencies = None
        self.first_date = None
        self.last_date = None
        self.dates = None

        if currency_file is None:
            self._load_file(DEF_CURRENCY_FILE)
        else:
            self._load_file(currency_file)


    def _load_file(self, currency_file):
        """Load the currency file in the main structure.
        """
        self._rates = defaultdict(dict)
        self.currencies = set()

        with open(currency_file) as file_:
            header = next(file_)
            currencies = header.strip().split(DELIMITER)[1:]

            for currency in currencies:
                if currency:
                    self.currencies.add(currency)
            self.currencies.add(REF_CURRENCY)

            for line in file_:
                line = line.strip().split(DELIMITER)

                # date, USD, JPY, ...
                date = datetime.strptime(line[0], DATE_FORMAT)
                rates = line[1:]

                for currency, rate in zip(currencies, rates):
                    # Get rid of empty currency at end of line
                    if currency:
                        if rate in NA_VALUES:
                            self._rates[date][currency] = None
                        else:
                            self._rates[date][currency] = float(rate)


        # Most recent date for rates
        self.dates = set(self._rates)
        self.first_date = min(self.dates)
        self.last_date = max(self.dates)


    def _get_closest_valid_date(self, date):
        """Compute closest valid date of a given date.

        >>> from datetime import datetime
        >>> c._get_closest_valid_date(datetime(1990, 1, 1))
        datetime.datetime(1999, 1, 4, 0, 0)
        """
        return min((abs(date - d), d) for d in self._rates)[1]


    def _get_closest_available_date(self, currency, date):
        """Compute closest available date of a given date/currency.

        >>> from datetime import datetime
        >>> c._get_closest_available_date('BGN', datetime(1999, 12, 1))
        datetime.datetime(2000, 7, 19, 0, 0)
        """
        # Notice that we do not catch the ValueError
        # occurring if one currency has only None
        # rates for all dates
        # This should not happen, given the data set
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

    parser.add_argument("amount")
    parser.add_argument("currency")

    parser.add_argument("-t", "--to",
        help="""
        To currency, default %(default)s
        """,
        default=REF_CURRENCY)

    parser.add_argument("-d", "--date",
        help="""
        Date for conversion, with format {0}
        """.format(DATE_FORMAT.replace('%', '%%')),
        default=None)

    parser.add_argument("-v", "--verbose",
        help="""
        Display additional information on data set.
        """,
        action='store_true')

    args = parser.parse_args()


    c = CurrencyConverter(fallback_on_wrong_date=True,
                          fallback_on_missing_rate=True,
                          verbose=True)

    print()
    print('Available currencies [{0}]:'.format(len(c.currencies)))
    for tuple_ in grouper(10, sorted(c.currencies), padvalue=''):
        print(' '.join(tuple_))

    print()
    print('First available date:', c.first_date.strftime(DATE_FORMAT))
    print('Last available date :', c.last_date.strftime(DATE_FORMAT))

    missing_dates = []
    for d in range((c.last_date - c.first_date).days + 1):
        date_inter = c.first_date + td(days=d)
        if date_inter not in c._rates:
            missing_dates.append(date_inter.strftime(DATE_FORMAT))

    if missing_dates:
        print('Missing [{0}/{1}]:'.format(
            len(missing_dates),
            (c.last_date - c.first_date).days + 1))

    if args.verbose:
        for tuple_ in grouper(10, sorted(missing_dates), padvalue=''):
            print(' '.join(tuple_))

    if args.date is not None:
        date = datetime.strptime(args.date, DATE_FORMAT)
    else:
        date = c.last_date

    new_amount = c.convert(args.amount, args.currency, args.to, date)

    print()
    print('"{0} {1}" is "{2} {3}" on {4}.'.format(
        args.amount,
        args.currency,
        new_amount,
        args.to,
        date.strftime(DATE_FORMAT)))


if __name__ == '__main__':

    main()

