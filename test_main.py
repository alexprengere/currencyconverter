#!/usr/bin/python
# -*- coding: utf-8 -*-

from datetime import datetime, date

import pytest
from currency_converter import (CurrencyConverter, S3CurrencyConverter,
                                RateNotFoundError)

c0 = CurrencyConverter()
c1 = CurrencyConverter(fallback_on_missing_rate=True)
c2 = CurrencyConverter(fallback_on_wrong_date=True)

converters = [c0, c1, c2]
converters_with_missing_rate_fallback = [c1]
converters_with_wrong_date_fallback = [c2]
converters_without_missing_rate_fallback = [c0, c2]
converters_without_wrong_date_fallback = [c0, c1]


def equals(a, b):
    return abs(b - a) < 1e-5


class TestRates(object):

    @pytest.mark.parametrize("c", converters)
    def test_convert(self, c):
        assert equals(c.convert(10, 'EUR', 'USD', date=date(2013, 3, 21)), 12.91)
        assert equals(c.convert(10, 'EUR', 'USD', date=date(2014, 3, 28)), 13.758999)
        assert equals(c.convert(10, 'USD', 'EUR', date=date(2014, 3, 28)), 7.26797)

    @pytest.mark.parametrize("c", converters)
    def test_convert_with_datetime(self, c):
        assert equals(c.convert(10, 'EUR', 'USD', date=datetime(2013, 3, 21)), 12.91)
        assert equals(c.convert(10, 'EUR', 'USD', date=datetime(2014, 3, 28)), 13.758999)
        assert equals(c.convert(10, 'USD', 'EUR', date=datetime(2014, 3, 28)), 7.26797)

    @pytest.mark.parametrize("c", converters)
    def test_convert_to_ref_currency(self, c):
        assert c.convert(10, 'EUR') == 10.
        assert c.convert(10, 'EUR', 'EUR') == 10.


class TestErrorCases(object):

    @pytest.mark.parametrize("c", converters)
    def test_wrong_currency(self, c):
        with pytest.raises(ValueError):
            c.convert(1, 'AAA')

    @pytest.mark.parametrize("c", converters_without_missing_rate_fallback)
    def test_convert_with_missing_rate(self, c):
        with pytest.raises(RateNotFoundError):
            c.convert(10, 'BGN', date=date(2010, 11, 21))

    @pytest.mark.parametrize("c", converters_with_missing_rate_fallback)
    def test_convert_fallback_on_missing_rate(self, c):
        assert equals(c1.convert(10, 'BGN', date=date(2010, 11, 21)), 5.11299)

    @pytest.mark.parametrize("c", converters_without_wrong_date_fallback)
    def test_convert_with_wrong_date(self, c):
        with pytest.raises(RateNotFoundError):
            c.convert(10, 'EUR', 'USD', date=date(1986, 2, 2))

    @pytest.mark.parametrize("c", converters_with_wrong_date_fallback)
    def test_convert_fallback_on_wrong_date(self, c):
        assert equals(c.convert(10, 'EUR', 'USD', date=date(1986, 2, 2)), 11.789)


class TestAttributes(object):

    @pytest.mark.parametrize("c", converters)
    def test_bounds(self, c):
        first_date, last_date = c.bounds['USD']
        assert first_date == date(1999, 1, 4)
        assert last_date == date(2016, 4, 29)

        first_date, last_date = c.bounds['BGN']
        assert first_date == date(2000, 7, 19)
        assert last_date == date(2016, 4, 29)

        first_date, last_date = c.bounds['EUR']
        assert first_date == date(1999, 1, 4)
        assert last_date == date(2016, 4, 29)

    @pytest.mark.parametrize("c", converters)
    def test_currencies(self, c):
        assert len(c.currencies) == 42
        assert 'EUR' in c.currencies


class TestS3(object):

    def test_S3_currency_file_required(self):
        with pytest.raises(TypeError):
            S3CurrencyConverter()

    def test_S3_currency_file_needs_get_contents_as_strings(self):
        with pytest.raises(AttributeError):
            S3CurrencyConverter('simple_string')