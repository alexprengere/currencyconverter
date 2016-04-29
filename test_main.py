#!/usr/bin/python
# -*- coding: utf-8 -*-

from datetime import date

import pytest
from currency_converter import S3CurrencyConverter, RateNotFoundError


def equals(a, b):
    return abs(b - a) < 1e-5


def test_convert(c0, c1, c2):
    for c in c0, c1, c2:
        assert c.convert(10, 'EUR', 'USD', date=date(2013, 3, 21)) == 12.91

def test_convert_ref_currency(c0, c1, c2):
    for c in c0, c1, c2:
        assert c.convert(10, 'EUR') == 10.
        assert c.convert(10, 'EUR', 'EUR') == 10.

def test_convert_with_missing_rate(c0, c2):
    for c in c0, c2:
        with pytest.raises(RateNotFoundError):
            c.convert(10, 'BGN', date=date(2010, 11, 21))

def test_convert_fallback_on_missing_rate(c1):
    assert equals(c1.convert(10, 'BGN', date=date(2010, 11, 21)), 5.11299)

def test_convert_with_wrong_date(c0, c1):
    for c in c0, c1:
        with pytest.raises(RateNotFoundError):
            c0.convert(10, 'EUR', 'USD', date=date(1986, 2, 2))

def test_convert_fallback_on_wrong_date(c2):
    assert equals(c2.convert(10, 'EUR', 'USD', date=date(1986, 2, 2)), 11.789)

def test_bounds(c0, c1, c2):
    for c in c0, c1, c2:
        first_date, last_date = c.bounds['USD']
        assert first_date == date(1999, 1, 4)
        assert last_date == date(2016, 4, 20)

        first_date, last_date = c.bounds['EUR']
        assert first_date == date(1999, 1, 4)
        assert last_date == date(2016, 4, 20)

def test_currencies(c0, c1, c2):
    for c in c0, c1, c2:
        assert len(c.currencies) == 42
        assert 'EUR' in c.currencies

def test_wrong_currency(c0, c1, c2):
    for c in c0, c1, c2:
        with pytest.raises(ValueError):
            c.convert(1, 'AAA')

def test_S3_currency_file_required():
    with pytest.raises(TypeError):
        S3CurrencyConverter()

def test_S3_currency_file_needs_get_contents_as_strings():
    with pytest.raises(AttributeError):
        S3CurrencyConverter('simple_string')
