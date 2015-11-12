Currency converter
==================

This is a currency converter that uses historical rates against a reference currency (Euro).

Currency sources
----------------
The default source is the `European Central Bank <http://www.ecb.int/>`_. This is the ECB historical rates for 42 currencies against the Euro since 1999.
It can be downloaded here: `eurofxref-hist.zip <http://www.ecb.int/stats/eurofxref/eurofxref-hist.zip>`_.
The converter can use different sources as long as the format is the same.

Installation
------------

You can install directly after cloning:

.. code-block:: bash

 $ python setup.py install --user

Or use the Python package:

.. code-block:: bash

  $ pip install --user currencyconverter

Command line example
--------------------

.. code-block:: bash

 $ python currency_converter.py 100 EUR --to USD
 "100 EUR" is "137.59 USD" on 2014-03-28.

After installation, you should have ``currency_converter`` in your ``$PATH``:

.. code-block:: bash

 $ currency_converter 100 USD -d 2013-12-12

Python API example
------------------

Example:

.. code-block:: python

    >>> from currency_converter import CurrencyConverter
    >>> c = CurrencyConverter()

Convert from EUR to USD:

.. code-block:: python

    >>> c.convert(100, 'EUR', 'USD') # doctest: +SKIP
    137.5...

Default target currency is EUR:

.. code-block:: python

    >>> c.convert(100, 'EUR')
    100.0
    >>> c.convert(100, 'USD') # doctest: +SKIP
    72.67...

Change reference date for rate:

.. code-block:: python

    >>> from datetime import datetime
    >>> c.convert(100, 'EUR', 'USD', date=datetime(2013, 3, 21))
    129.1...

Get a rate:

.. code-block:: python

    >>> c.get_rate('USD') # doctest: +SKIP
    1.375...

Fallback mode on not supported dates:

.. code-block:: python

    >>> c = CurrencyConverter(fallback_on_wrong_date=True, verbose=True)
    >>> c.convert(100, 'EUR', 'USD', date=datetime(1986, 2, 2))
    /!\ Invalid date (currency was EUR), fallback to 1999-01-04
    /!\ Invalid date (currency was USD), fallback to 1999-01-04
    117.89...

Sometimes rates are missing:

.. code-block:: python

    >>> c.convert(100, 'BGN', date=datetime(1999, 11, 10))
    Traceback (most recent call last):
    RateNotFoundError: Currency BGN has no rate for date 1999-11-10.

But we also have a fallback mode for those:

.. code-block:: python

    >>> c = CurrencyConverter(fallback_on_wrong_date=True,
    ...                       fallback_on_missing_rate=True,
    ...                       verbose=True)
    >>> c.convert(100, 'BGN', date=datetime(1999, 11, 10))
    /!\ Missing rate for BGN, fallback to 2000-07-19
    51.36...
    >>> c.convert(100, 'BGN', 'EUR', date=datetime(1980, 1, 1))
    /!\ Invalid date (currency was BGN), fallback to 1999-01-04
    /!\ Missing rate for BGN, fallback to 2000-07-19
    /!\ Invalid date (currency was EUR), fallback to 1999-01-04
    51.36...

Other public members:

.. code-block:: python

    >>> c.last_date
    datetime.datetime(2015, 11, 12, 0, 0)
    >>> min(c.dates)
    datetime.datetime(1999, 1, 4, 0, 0)
    >>> sorted(c.currencies)
    ['AUD', 'BGN', 'BRL', 'CAD', 'CHF', 'CNY', 'CYP', 'CZK', 'DKK', ...

Error cases:

.. code-block:: python

    >>> c = CurrencyConverter()
    >>> c.get_rate('BGN', date=datetime(1999, 11, 10)) # None, rate is missing
    >>> c.get_rate('AAA')
    Traceback (most recent call last):
    ValueError: Currency AAA not supported.

