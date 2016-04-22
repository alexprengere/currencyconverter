#!/usr/bin/python
# -*- coding: utf-8 -*-

import unittest
import doctest

import currency_converter.currency_converter as cc # actual module
from currency_converter import CurrencyConverter, S3CurrencyConverter

from datetime import datetime

class CurrencyConverterTest(unittest.TestCase):

    def setUp(self):
        self.c = CurrencyConverter()

    def test_convert(self):
        self.assertEqual(self.c.convert(100, 'EUR'), 100.)

    def test_closest_valid_date_go_down(self):
        expected = datetime(2016, 4, 15)
        actual = self.c._get_closest_valid_date(datetime(2016, 4, 16))
        self.assertEqual(expected, actual)

    def test_closest_valid_date_go_up(self):
        expected = datetime(2016, 4, 18)
        actual = self.c._get_closest_valid_date(datetime(2016, 4, 17))
        self.assertEqual(expected, actual)

    def test_closest_valid_date_stay(self):
        expected = datetime(2016, 4, 18)
        actual = self.c._get_closest_valid_date(datetime(2016, 4, 17))
        self.assertEqual(expected, actual)

    def test_closest_valid_way_off(self):
        expected = datetime(1999, 1, 4)
        actual = self.c._get_closest_valid_date(datetime(1245, 4, 17))
        self.assertEqual(expected, actual)

class S3CurrencyConverterTest(unittest.TestCase):

    def test_currency_file_required(self):
        with self.assertRaises(TypeError):
            #pylint: disable=no-value-for-parameter
            S3CurrencyConverter()

    def test_currency_file_needs_get_contents_as_strings(self):
        with self.assertRaises(AttributeError):
            S3CurrencyConverter('simple_string')


def main():

    extraglobs = {
        'c': CurrencyConverter(),
    }

    opt = (doctest.ELLIPSIS |
           doctest.NORMALIZE_WHITESPACE |
           doctest.IGNORE_EXCEPTION_DETAIL)

    s = unittest.TestSuite()

    s.addTests(unittest.makeSuite(CurrencyConverterTest))
    s.addTests(unittest.makeSuite(S3CurrencyConverterTest))
    s.addTests(doctest.DocTestSuite(cc, extraglobs=extraglobs, optionflags=opt))
    s.addTests(doctest.DocFileSuite('README.rst', optionflags=opt))

    return s


if __name__ == '__main__':

    unittest.main(defaultTest='main')

