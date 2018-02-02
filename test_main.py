#!/usr/bin/python
# -*- coding: utf-8 -*-

from datetime import datetime, date, timedelta
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

import pytest
from currency_converter import (CurrencyConverter, S3CurrencyConverter,
                                RateNotFoundError)

c0 = CurrencyConverter()
c1 = CurrencyConverter(fallback_on_missing_rate=True)
c2 = CurrencyConverter(fallback_on_wrong_date=True)
c3 = CurrencyConverter(fallback_on_missing_rate=True, fallback_on_wrong_date=True)
c4 = CurrencyConverter('./currency_converter/eurofxref-hist.zip')

converters = [c0, c1, c2, c3, c4]
converters_with_missing_rate_fallback = [c1, c3]
converters_with_wrong_date_fallback = [c2, c3]
converters_without_missing_rate_fallback = [c0, c2, c4]
converters_without_wrong_date_fallback = [c0, c1, c4]


def equals(a, b):
    return abs(b - a) < 1e-5


class TestRates(object):

    @pytest.mark.parametrize('c', converters)
    def test_convert(self, c):
        assert equals(c.convert(10, 'EUR', 'USD', date(2013, 3, 21)), 12.91)
        assert equals(c.convert(10, 'EUR', 'USD', date(2014, 3, 28)), 13.758999)
        assert equals(c.convert(10, 'USD', 'EUR', date(2014, 3, 28)), 7.26797)

    @pytest.mark.parametrize('c', converters)
    def test_convert_with_datetime(self, c):
        assert equals(c.convert(10, 'EUR', 'USD', datetime(2013, 3, 21)), 12.91)
        assert equals(c.convert(10, 'EUR', 'USD', datetime(2014, 3, 28)), 13.758999)
        assert equals(c.convert(10, 'USD', 'EUR', datetime(2014, 3, 28)), 7.26797)

    @pytest.mark.parametrize('c', converters)
    def test_convert_to_ref_currency(self, c):
        assert c.convert(10, 'EUR') == 10.
        assert c.convert(10, 'EUR', 'EUR') == 10.


class TestErrorCases(object):

    @pytest.mark.parametrize('c', converters)
    def test_wrong_currency(self, c):
        with pytest.raises(ValueError):
            c.convert(1, 'AAA')

    @pytest.mark.parametrize('c', converters_without_missing_rate_fallback)
    def test_convert_with_missing_rate(self, c):
        with pytest.raises(RateNotFoundError):
            c.convert(10, 'BGN', date=date(2010, 11, 21))

    @pytest.mark.parametrize('c', converters_with_missing_rate_fallback)
    def test_convert_fallback_on_missing_rate(self, c):
        assert equals(c1.convert(10, 'BGN', date=date(2010, 11, 21)), 5.11299)

    @pytest.mark.parametrize('c', converters_without_wrong_date_fallback)
    def test_convert_with_wrong_date(self, c):
        with pytest.raises(RateNotFoundError):
            c.convert(10, 'EUR', 'USD', date=date(1986, 2, 2))

    @pytest.mark.parametrize('c', converters_with_wrong_date_fallback)
    def test_convert_fallback_on_wrong_date(self, c):
        assert equals(c.convert(10, 'EUR', 'USD', date=date(1986, 2, 2)), 11.789)


def last_n_days(n):
    return [date.today() - timedelta(days=d)
            for d in reversed(range(n + 1))]


class TestAttributes(object):

    @pytest.mark.parametrize('c', converters)
    def test_bounds(self, c):
        assert c.bounds['USD'][0] == date(1999, 1, 4)
        assert c.bounds['BGN'][0] == date(2000, 7, 19)
        assert c.bounds['EUR'][0] == date(1999, 1, 4)

        assert c.bounds['USD'][1] in last_n_days(3)
        assert c.bounds['BGN'][1] in last_n_days(3)
        assert c.bounds['EUR'][1] in last_n_days(3)

    @pytest.mark.parametrize('c', converters)
    def test_currencies(self, c):
        assert len(c.currencies) == 42
        assert 'EUR' in c.currencies


class TestCustomObject(object):

    c = CurrencyConverter(currency_file=None,
                          fallback_on_wrong_date=True,
                          fallback_on_missing_rate=True)

    c.load_lines(StringIO('''\
    Date,USD,AAA,
    2014-03-29,2,N/A
    2014-03-27,6,0
    2014-03-23,18,N/A
    2014-03-22,N/A,0'''))

    def test_convert(self):
        assert equals(self.c.convert(10, 'EUR', 'USD'), 20)
        assert equals(self.c.convert(10, 'USD', 'EUR'), 5)

    def test_fallback_date(self):
        # Fallback to 2014-03-29 rate of 2
        assert equals(self.c.convert(10, 'EUR', 'USD', date(2015, 1, 1)), 20)
        assert equals(self.c.convert(10, 'USD', 'EUR', date(2015, 1, 1)), 5)

        # Fallback to 2014-03-23 rate of 18
        assert equals(self.c.convert(10, 'EUR', 'USD', date(2012, 1, 1)), 180)
        assert equals(self.c.convert(10, 'USD', 'EUR', date(2012, 1, 1)), 0.555555)

    def test_fallback_rate(self):
        # Fallback rate is the average between 2 and 6, so 4
        assert equals(self.c.convert(10, 'EUR', 'USD', date(2014, 3, 28)), 40)
        assert equals(self.c.convert(10, 'USD', 'EUR', date(2014, 3, 28)), 2.5)

        # Fallback rate is the weighted mean between 6 (d:1) and 18 (d:3), so 9
        assert equals(self.c.convert(10, 'EUR', 'USD', date(2014, 3, 26)), 90)
        assert equals(self.c.convert(10, 'USD', 'EUR', date(2014, 3, 26)), 1.11111)

    def test_attributes(self):
        assert self.c.currencies == set(['EUR', 'USD', 'AAA'])
        assert self.c.bounds == {
            'USD': (date(2014, 3, 23), date(2014, 3, 29)),
            'AAA': (date(2014, 3, 22), date(2014, 3, 27)),
            # Max of previous ranges
            'EUR': (date(2014, 3, 22), date(2014, 3, 29))
        }


def test_single_day_file():
    c = CurrencyConverter('http://www.ecb.europa.eu/stats/eurofxref/eurofxref.zip')
    assert len(c.currencies) == 33


class TestCustomSource(object):

    def test_local_zip_file(self):
        c = CurrencyConverter('./currency_converter/eurofxref-hist.zip')
        assert len(c.currencies) == 42
        assert equals(c.convert(10, 'EUR', 'USD', date(2013, 3, 21)), 12.91)

    def test_remote_zip_file(self):
        c = CurrencyConverter('http://www.ecb.int/stats/eurofxref/eurofxref-hist.zip')
        assert len(c.currencies) == 42
        assert equals(c.convert(10, 'EUR', 'USD', date(2013, 3, 21)), 12.91)

    def test_local_clear_file(self):
        c = CurrencyConverter('./currency_converter/test_single_day.csv')
        assert len(c.currencies) == 32

    def test_remote_clear_file(self):
        c = CurrencyConverter('https://raw.githubusercontent.com/alexprengere'
                              '/currencyconverter/master/currency_converter/test_single_day.csv')
        assert len(c.currencies) == 32


class TestS3(object):

    def test_S3_currency_file_required(self):
        with pytest.raises(TypeError):
            S3CurrencyConverter()

    def test_S3_currency_file_needs_get_contents_as_strings(self):
        with pytest.raises(AttributeError):
            S3CurrencyConverter('simple_string')
