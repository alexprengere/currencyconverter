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

Launch the tests with `tox`:

.. code-block:: bash

 $ tox

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

    >>> from datetime import date
    >>> c.convert(100, 'EUR', 'USD', date=date(2013, 3, 21))
    129.1...
    >>> from datetime import datetime # works too ;)
    >>> c.convert(100, 'EUR', 'USD', date=datetime(2013, 3, 21))
    129.1...

Get a rate:

.. code-block:: python

    >>> c.get_rate('USD', date=date(2013, 3, 21))
    1.291

Sometimes rates are missing:

.. code-block:: python

    >>> c.convert(100, 'BGN', date=date(2010, 11, 21))
    Traceback (most recent call last):
    RateNotFoundError: BGN has no rate for 2010-11-21

But we have a fallback mode for those, using a linear interpolation of the
closest known rates, as long as you ask for a date within the currency date bounds:

.. code-block:: python

    >>> c = CurrencyConverter(fallback_on_missing_rate=True)
    >>> c.convert(100, 'BGN', date=date(2010, 11, 21))
    51.12...

We also have a fallback mode when asking dates outside of the currency bounds:

.. code-block:: python

    >>> c = CurrencyConverter()
    >>> c.convert(100, 'EUR', 'USD', date=date(1986, 2, 2))
    Traceback (most recent call last):
    ValueError: 1986-02-02 not in USD bounds 1999-01-04/2016-04-20
    >>> 
    >>> c = CurrencyConverter(fallback_on_wrong_date=True, verbose=True)
    AUD: 1888 missing rates from 1999-01-04 to ...
    >>> c.convert(100, 'EUR', 'USD', date=date(1986, 2, 2))
    1986-02-02 not in USD bounds 1999-01-04/2016-04-20, falling back to closest one
    117.89...

Use your own currency file with the same format:

.. code-block:: python

    >>> c = CurrencyConverter('./path/to/currency/file.csv') # doctest: +SKIP

Other public members:

.. code-block:: python

    >>> first_date, last_date = c.bounds['USD']
    >>> first_date
    datetime.date(1999, 1, 4)
    >>> last_date
    datetime.date(2016, 4, 20)
    >>> sorted(c.currencies)
    ['AUD', 'BGN', 'BRL', 'CAD', 'CHF', 'CNY', 'CYP', 'CZK', 'DKK', ...

Error cases:

.. code-block:: python

    >>> c = CurrencyConverter()
    >>> c.convert(100, 'AAA')
    Traceback (most recent call last):
    ValueError: AAA is not a supported currency

