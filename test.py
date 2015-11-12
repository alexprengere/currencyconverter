#!/usr/bin/python
# -*- coding: utf-8 -*-

import unittest
import doctest

import currency_converter as cc


class CurrencyConverterTest(unittest.TestCase):

    def setUp(self):
        self.cc = cc.CurrencyConverter()

    def test_convert(self):
        self.assertEquals(self.cc.convert(100, 'EUR'), 100.)


def main():

    extraglobs = {
        'c': cc.CurrencyConverter(),
    }

    opt = (doctest.ELLIPSIS |
           doctest.NORMALIZE_WHITESPACE)

    s = unittest.TestSuite()

    s.addTests(unittest.makeSuite(CurrencyConverterTest))
    s.addTests(doctest.DocTestSuite(cc.currency_converter, extraglobs=extraglobs, optionflags=opt))
    s.addTests(doctest.DocFileSuite('README.rst', optionflags=opt))

    return s


if __name__ == '__main__':

    unittest.main(defaultTest='main')

