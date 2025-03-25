#!/usr/bin/env python

import os.path as op
from functools import wraps
import datetime
from datetime import timedelta
from collections import defaultdict, namedtuple
from zipfile import ZipFile
from io import BytesIO
from decimal import Decimal
from urllib.request import urlopen

_DIRNAME = op.realpath(op.dirname(__file__))
CURRENCY_FILE = op.join(_DIRNAME, "eurofxref-hist.zip")
SINGLE_DAY_CURRENCY_FILE = op.join(_DIRNAME, "eurofxref.csv")
ECB_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.zip"
SINGLE_DAY_ECB_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref.zip"

Bounds = namedtuple("Bounds", "first_date last_date")

__all__ = [
    "CURRENCY_FILE",
    "ECB_URL",
    "SINGLE_DAY_CURRENCY_FILE",
    "SINGLE_DAY_ECB_URL",
    "CurrencyConverter",
    "RateNotFoundError",
    "S3CurrencyConverter",
]


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
    return [
        first_date + timedelta(days=n) for n in range(1 + (last_date - first_date).days)
    ]


@memoize
def parse_date(s):
    """Fast %Y-%m-%d parsing."""
    try:
        return datetime.date(int(s[:4]), int(s[5:7]), int(s[8:10]))
    except ValueError:  # other accepted format used in one-day data set
        return datetime.datetime.strptime(s, "%d %B %Y").date()


def get_lines_from_zip(zip_str):
    zip_file = ZipFile(BytesIO(zip_str))
    for name in zip_file.namelist():
        yield from zip_file.read(name).decode("utf-8").splitlines()


class RateNotFoundError(Exception):
    """Custom exception when data is missing in the rates file."""


class CurrencyConverter:
    """
    At init, load the historic currencies (since 1999) from the ECB.
    The rates are EUR foreign exchange reference rates:

    Date,USD,JPY,BGN,CYP,CZK,...
    2014-03-28,1.3759,140.9,1.9558,N/A,27.423,...
    2014-03-27,1.3758,...

    ``_rates`` is a dictionary with:

    - currencies as keys
    - {date: rate, ...} as values.

    ``currencies`` is a set of all available currencies.
    ``bounds`` is a dict if first and last date available per currency.
    """

    def __init__(
        self,
        currency_file=CURRENCY_FILE,
        fallback_on_wrong_date=False,
        fallback_on_missing_rate=False,
        fallback_on_missing_rate_method="linear_interpolation",
        ref_currency="EUR",
        na_values=frozenset(["", "N/A"]),
        decimal=False,
        verbose=False,
    ):
        """Instantiate a CurrencyConverter.

        :param str currency_file: Path to the source data. Can be a local path,
            or an URL starting with 'http://' or 'https://'. Defaults to the
            European Central Bank historical rates file included in the package.
        :param bool fallback_on_wrong_date: Set to False (default) to raise a
            RateNotFoundError when dates are requested outside the data's range.
            Set to True to extrapolate rates for dates outside the source data's
            range. The extrapolation is done by falling back to the first or
            last data point, for dates before and after the data's range,
            respectively.
        :param bool fallback_on_missing_rate: Set to True to linearly
            interpolate missing rates by their two closest valid rates. This
            only affects dates within the source data's range. Default False.
            Set to False to raise RateNotFoundError when hitting a missing rate,
            e.g. on weekends or banking holidays.
        :param str fallback_on_missing_rate_method: Choose the fallback on missing
            rate method. Default is "linear_interpolation", also available is "last_known".
        :param str ref_currency: Three-letter currency code for the currency
            that the source data is oriented towards. This is EUR for the
            default European Central Bank data, and so the default is 'EUR'.
        :param iterable na_values: What to interpret as missing values in the
            source data.
        :param decimal: Set to True to use decimal.Decimal internally, this will
            slow the loading time but will allow exact conversions
        :param verbose: Set to True to print what is going on under the hood.
        """
        # Global options
        self.fallback_on_wrong_date = fallback_on_wrong_date
        self.fallback_on_missing_rate = fallback_on_missing_rate
        self.fallback_on_missing_rate_method = fallback_on_missing_rate_method
        self.ref_currency = ref_currency  # reference currency of rates
        self.na_values = na_values  # missing values
        self.cast = Decimal if decimal else float
        self.verbose = verbose

        # Will be filled once the file is loaded
        self._rates = None
        self.bounds = None
        self.currencies = None

        if currency_file is not None:
            self.load_file(currency_file)

    def load_file(self, currency_file):
        """To be subclassed if alternate methods of loading data."""
        if currency_file.startswith(("http://", "https://")):
            content = urlopen(currency_file).read()
        else:
            with open(currency_file, "rb") as f:
                content = f.read()

        if currency_file.endswith(".zip"):
            self.load_lines(get_lines_from_zip(content))
        else:
            self.load_lines(content.decode("utf-8").splitlines())

    def load_lines(self, lines):
        _rates = self._rates = defaultdict(dict)
        na_values = self.na_values
        cast = self.cast

        lines = iter(lines)
        header = next(lines).strip().split(",")[1:]

        for line in lines:
            line = line.strip().split(",")
            date = parse_date(line[0])
            for currency, rate in zip(header, line[1:]):
                currency = currency.strip()
                if rate not in na_values and currency:  # skip empty currency
                    _rates[currency][date] = cast(rate)

        self.currencies = set(self._rates) | {self.ref_currency}
        self._compute_bounds()

        for currency in sorted(self._rates):
            self._set_missing_to_none(currency)
            if self.fallback_on_missing_rate:
                method = self.fallback_on_missing_rate_method
                if method == "linear_interpolation":
                    self._use_linear_interpolation(currency)
                elif method == "last_known":
                    self._use_last_known(currency)
                else:
                    raise ValueError(f"Unknown fallback method {method!r}")

    def _compute_bounds(self):
        self.bounds = {
            currency: Bounds(min(r), max(r)) for currency, r in self._rates.items()
        }

        self.bounds[self.ref_currency] = Bounds(
            min(b.first_date for b in self.bounds.values()),
            max(b.last_date for b in self.bounds.values()),
        )

    def _set_missing_to_none(self, currency):
        """Fill missing rates of a currency with the closest available ones."""
        rates = self._rates[currency]
        first_date, last_date = self.bounds[currency]

        for date in list_dates_between(first_date, last_date):
            if date not in rates:
                rates[date] = None

        if self.verbose:
            missing = len([r for r in rates.values() if r is None])
            if missing:
                print(
                    f"{currency}: {missing} missing rates from {first_date} to {last_date}"
                    f" ({1 + (last_date - first_date).days} days)"
                )

    def _use_linear_interpolation(self, currency):
        """Fill missing rates of a currency.

        This is done by linear interpolation of the two closest available rates.

        :param str currency: The currency to fill missing rates for.
        """
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
                print(
                    f"{currency}: filling {date} missing rate using"
                    f" {r0} ({d0}d old) and {r1} ({d1}d later)"
                )

    def _use_last_known(self, currency):
        """Fill missing rates of a currency.

        This is done by using the last known rate.

        :param str currency: The currency to fill missing rates for.
        """
        rates = self._rates[currency]

        for date in sorted(rates):
            rate = rates[date]
            if rate is not None:
                last_rate, last_date = rate, date
            else:
                rates[date] = last_rate
                if self.verbose:
                    print(
                        f"{currency}: filling {date} missing rate using"
                        f" {last_rate} from {last_date}"
                    )

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
            return self.cast("1")

        if date not in self._rates[currency]:
            first_date, last_date = self.bounds[currency]

            if not self.fallback_on_wrong_date:
                raise RateNotFoundError(
                    f"{date} not in {currency} bounds {first_date}/{last_date}"
                )

            if date < first_date:
                fallback_date = first_date
            elif date > last_date:
                fallback_date = last_date
            else:
                raise AssertionError("Should never happen, bug in the code!")

            if self.verbose:
                print(
                    rf"/!\ {date} not in {currency} bounds {first_date}/{last_date},"
                    f" falling back to {fallback_date}"
                )

            date = fallback_date

        rate = self._rates[currency][date]
        if rate is None:
            raise RateNotFoundError(f"{currency} has no rate for {date}")
        return rate

    def convert(self, amount, currency, new_currency="EUR", date=None):
        """Convert amount from a currency to another one.

        :param float amount: The amount of `currency` to convert.
        :param str currency: The currency to convert from.
        :param str new_currency: The currency to convert to.
        :param datetime.date date: Use the conversion rate of this date. If this
            is not given, the most recent rate is used.

        :return: The value of `amount` in `new_currency`.
        :rtype: float

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
        for c in currency, new_currency:
            if c not in self.currencies:
                raise ValueError(f"{c} is not a supported currency")

        if date is None:
            date = self.bounds[currency].last_date
        else:
            try:
                date = date.date()  # fallback if input was a datetime object
            except AttributeError:
                pass

        r0 = self._get_rate(currency, date)
        r1 = self._get_rate(new_currency, date)

        return self.cast(amount) / r0 * r1


class S3CurrencyConverter(CurrencyConverter):
    """
    Load the ECB CSV file from an S3 key instead of from a local file.
    The first argument should be an instance of boto.s3.key.Key (or any other
    object that provides a get_contents_as_string() method which returns the
    CSV file as a string).
    """

    def __init__(self, currency_file, **kwargs):
        """Make currency_file a required attribute"""
        super().__init__(currency_file, **kwargs)

    def load_file(self, currency_file):
        lines = currency_file.get_contents_as_string().splitlines()
        self.load_lines(lines)
