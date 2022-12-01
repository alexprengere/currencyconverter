#!/usr/bin/python
# -*- coding: utf-8 -*-

from decimal import Decimal
from datetime import datetime, date, timedelta

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

import pytest
from pytest import approx
from currency_converter import (
    CurrencyConverter,
    S3CurrencyConverter,
    RateNotFoundError,
    ECB_URL,
    CURRENCY_FILE,
    SINGLE_DAY_ECB_URL,
    SINGLE_DAY_CURRENCY_FILE,
)

c0 = CurrencyConverter()
c1 = CurrencyConverter(fallback_on_missing_rate=True)
c2 = CurrencyConverter(fallback_on_wrong_date=True)
c3 = CurrencyConverter(
    fallback_on_missing_rate=True,
    fallback_on_wrong_date=True,
    fallback_on_missing_rate_method="linear_interpolation",
)
c4 = CurrencyConverter(
    fallback_on_missing_rate=True,
    fallback_on_wrong_date=True,
    fallback_on_missing_rate_method="last_known",
)
c5 = CurrencyConverter(CURRENCY_FILE)

converters = [c0, c1, c2, c3, c4, c5]
converters_with_missing_rate_fallback = [c1, c3, c4]
converters_with_wrong_date_fallback = [c2, c3, c4]
converters_without_missing_rate_fallback = [c0, c2, c5]
converters_without_wrong_date_fallback = [c0, c1, c5]


@pytest.fixture
def fallback_with_linear_interpolation():
    return c3


@pytest.fixture
def fallback_with_last_known():
    return c4


@pytest.fixture
def decimal_converter():
    return CurrencyConverter(decimal=True)


HISTORY_CURRENCIES = {
    "HUF",
    "LVL",
    "RON",
    "ISK",
    "SIT",
    "CHF",
    "DKK",
    "MYR",
    "PHP",
    "KRW",
    "HKD",
    "IDR",
    "HRK",
    "MTL",
    "LTL",
    "CZK",
    "CYP",
    "NZD",
    "ZAR",
    "NOK",
    "AUD",
    "SGD",
    "THB",
    "CNY",
    "SKK",
    "GBP",
    "TRL",
    "TRY",
    "JPY",
    "BGN",
    "USD",
    "CAD",
    "RUB",
    "SEK",
    "EUR",
    "BRL",
    "ROL",
    "PLN",
    "EEK",
    "ILS",
    "MXN",
    "INR",
}

SINGLE_DAY_CURRENCIES = {
    "BRL",
    "CZK",
    "PHP",
    "THB",
    "NOK",
    "PLN",
    "SGD",
    "BGN",
    "HKD",
    "MYR",
    "ISK",
    "CAD",
    "KRW",
    "JPY",
    "DKK",
    "ZAR",
    "RON",
    "IDR",
    "NZD",
    "INR",
    "MXN",
    "TRY",
    "USD",
    "HRK",
    "CNY",
    "HUF",
    "EUR",
    "GBP",
    "SEK",
    "AUD",
    "ILS",
    "CHF",
}


class TestRates(object):
    @pytest.mark.parametrize("c", converters)
    def test_convert(self, c):
        assert c.convert(10, "EUR", "USD", date(2013, 3, 21)) == approx(12.91)
        assert c.convert(10, "EUR", "USD", date(2014, 3, 28)) == approx(13.758999)
        assert c.convert(10, "USD", "EUR", date(2014, 3, 28)) == approx(7.26797)

    @pytest.mark.parametrize("c", converters)
    def test_convert_with_datetime(self, c):
        assert c.convert(10, "EUR", "USD", datetime(2013, 3, 21)) == approx(12.91)
        assert c.convert(10, "EUR", "USD", datetime(2014, 3, 28)) == approx(13.758999)
        assert c.convert(10, "USD", "EUR", datetime(2014, 3, 28)) == approx(7.26797)

    @pytest.mark.parametrize("c", converters)
    def test_convert_to_ref_currency(self, c):
        assert c.convert(10, "EUR") == 10.0
        assert c.convert(10, "EUR", "EUR") == 10.0

    def test_decimal_converter(self, decimal_converter):
        dc = decimal_converter
        assert dc.convert(10, "EUR", "USD", date(2013, 3, 21)) == Decimal("12.910")
        assert dc.convert(10, "EUR", "USD", date(2014, 3, 28)) == Decimal("13.7590")
        assert dc.convert(10, "USD", "EUR", date(2014, 3, 28)) == Decimal(
            "7.267970055963369430917944618"
        )
        assert dc.convert(10, "EUR") == Decimal("10")
        assert dc.convert(10, "EUR", "EUR") == Decimal("10")


class TestErrorCases(object):
    @pytest.mark.parametrize("c", converters)
    def test_wrong_currency(self, c):
        with pytest.raises(ValueError):
            c.convert(1, "AAA")

    @pytest.mark.parametrize("c", converters_without_missing_rate_fallback)
    def test_convert_with_missing_rate(self, c):
        with pytest.raises(RateNotFoundError):
            c.convert(10, "BGN", date=date(2010, 11, 21))

    @pytest.mark.parametrize("c", converters_with_missing_rate_fallback)
    def test_convert_fallback_on_missing_rate(self, c):
        assert c1.convert(10, "BGN", date=date(2010, 11, 21)) == approx(5.112997238)

    @pytest.mark.parametrize("c", converters_without_wrong_date_fallback)
    def test_convert_with_wrong_date(self, c):
        with pytest.raises(RateNotFoundError):
            c.convert(10, "EUR", "USD", date=date(1986, 2, 2))

    @pytest.mark.parametrize("c", converters_with_wrong_date_fallback)
    def test_convert_fallback_on_wrong_date(self, c):
        assert c.convert(10, "EUR", "USD", date=date(1986, 2, 2)) == approx(11.789)

    def test_fallback_methds(
        self, fallback_with_linear_interpolation, fallback_with_last_known
    ):
        li = fallback_with_linear_interpolation
        ln = fallback_with_last_known
        assert li.convert(10, "USD", date=date(2019, 12, 8)) == approx(9.02418)
        assert ln.convert(10, "USD", date=date(2019, 12, 8)) == approx(9.01388)


def last_n_days(n):
    return [date.today() - timedelta(days=d) for d in reversed(range(n + 1))]


class TestAttributes(object):
    @pytest.mark.parametrize("c", converters)
    def test_bounds(self, c):
        assert c.bounds["USD"][0] == date(1999, 1, 4)
        assert c.bounds["BGN"][0] == date(2000, 7, 19)
        assert c.bounds["EUR"][0] == date(1999, 1, 4)

        assert c.bounds["USD"][1] in last_n_days(7)
        assert c.bounds["BGN"][1] in last_n_days(7)
        assert c.bounds["EUR"][1] in last_n_days(7)

    @pytest.mark.parametrize("c", converters)
    def test_currencies(self, c):
        assert "EUR" in c.currencies
        assert c.currencies == HISTORY_CURRENCIES


class TestCustomObject(object):

    c = CurrencyConverter(
        currency_file=None, fallback_on_wrong_date=True, fallback_on_missing_rate=True
    )

    c.load_lines(
        StringIO(
            """\
    Date,USD,AAA,
    2014-03-29,2,N/A
    2014-03-27,6,0
    2014-03-23,18,N/A
    2014-03-22,N/A,0"""
        )
    )

    def test_convert(self):
        assert self.c.convert(10, "EUR", "USD") == approx(20)
        assert self.c.convert(10, "USD", "EUR") == approx(5)

    def test_fallback_date(self):
        # Fallback to 2014-03-29 rate of 2
        assert self.c.convert(10, "EUR", "USD", date(2015, 1, 1)) == approx(20)
        assert self.c.convert(10, "USD", "EUR", date(2015, 1, 1)) == approx(5)

        # Fallback to 2014-03-23 rate of 18
        assert self.c.convert(10, "EUR", "USD", date(2012, 1, 1)) == approx(180)
        assert self.c.convert(10, "USD", "EUR", date(2012, 1, 1)) == approx(0.55555555)

    def test_fallback_rate(self):
        # Fallback rate is the average between 2 and 6, so 4
        assert self.c.convert(10, "EUR", "USD", date(2014, 3, 28)) == approx(40)
        assert self.c.convert(10, "USD", "EUR", date(2014, 3, 28)) == approx(2.5)

        # Fallback rate is the weighted mean between 6 (d:1) and 18 (d:3), so 9
        assert self.c.convert(10, "EUR", "USD", date(2014, 3, 26)) == approx(90)
        assert self.c.convert(10, "USD", "EUR", date(2014, 3, 26)) == approx(1.11111111)

    def test_attributes(self):
        assert self.c.currencies == {"EUR", "USD", "AAA"}
        assert self.c.bounds == {
            "USD": (date(2014, 3, 23), date(2014, 3, 29)),
            "AAA": (date(2014, 3, 22), date(2014, 3, 27)),
            # Max of previous ranges
            "EUR": (date(2014, 3, 22), date(2014, 3, 29)),
        }


@pytest.mark.parametrize(
    "c",
    [
        CurrencyConverter(SINGLE_DAY_ECB_URL),
        CurrencyConverter(SINGLE_DAY_CURRENCY_FILE),
    ],
)
def test_single_day_sources(c):
    assert c.currencies == SINGLE_DAY_CURRENCIES
    assert c.bounds["USD"][0] == c.bounds["USD"][1]
    assert c.bounds["USD"][0] in last_n_days(7)


class TestCustomSource(object):
    def test_local_zip_file(self):
        c = CurrencyConverter(CURRENCY_FILE)
        assert c.currencies == HISTORY_CURRENCIES
        assert c.convert(10, "EUR", "USD", date(2013, 3, 21)) == approx(12.91)

    def test_remote_zip_file(self):
        c = CurrencyConverter(ECB_URL)
        assert c.currencies == HISTORY_CURRENCIES
        assert c.convert(10, "EUR", "USD", date(2013, 3, 21)) == approx(12.91)

    def test_local_clear_file(self):
        c = CurrencyConverter(SINGLE_DAY_CURRENCY_FILE)
        assert c.currencies == SINGLE_DAY_CURRENCIES

    def test_remote_clear_file(self):
        c = CurrencyConverter(
            "https://raw.githubusercontent.com/alexprengere"
            "/currencyconverter/master/currency_converter/eurofxref.csv"
        )
        assert c.currencies == SINGLE_DAY_CURRENCIES


class TestS3(object):
    def test_S3_currency_file_required(self):
        with pytest.raises(TypeError):
            S3CurrencyConverter()

    def test_S3_currency_file_needs_get_contents_as_strings(self):
        with pytest.raises(AttributeError):
            S3CurrencyConverter("simple_string")
