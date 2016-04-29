#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import with_statement, print_function, division

import pytest
from currency_converter import CurrencyConverter


@pytest.fixture(scope='session')
def c0():
    return CurrencyConverter()


@pytest.fixture(scope='session')
def c1():
    return CurrencyConverter(fallback_on_missing_rate=True)


@pytest.fixture(scope='session')
def c2():
    return CurrencyConverter(fallback_on_wrong_date=True)
