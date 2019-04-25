#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import with_statement

from setuptools import setup, find_packages


with open('README.rst') as fl:
    LONG_DESCRIPTION = fl.read()

with open('LICENSE') as fl:
    LICENSE = fl.read()


setup(
    name='CurrencyConverter',
    version='0.13.9',
    author='Alex Prengère',
    author_email='alexprengere@gmail.com',
    url='https://github.com/alexprengere/currencyconverter',
    description='A currency converter using the European Central Bank data.',
    long_description=LONG_DESCRIPTION,
    license=LICENSE,
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=[],
    entry_points={
        'console_scripts' : [
            'currency_converter=currency_converter.__main__:main'
        ]
    },
)
