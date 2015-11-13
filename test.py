#!/usr/bin/python
# -*- coding: utf-8 -*-

import unittest
import doctest

import currency_converter.currency_converter as cc # actual module
from currency_converter import CurrencyConverter, S3CurrencyConverter


class CurrencyConverterTest(unittest.TestCase):

    def setUp(self):
        self.c = CurrencyConverter()

    def test_convert(self):
        self.assertEqual(self.c.convert(100, 'EUR'), 100.)


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

