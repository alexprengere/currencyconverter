Currency converter
==================

This is a currency converter that uses historical rates against a reference currency (Euro).

Currency data sources
---------------------

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

Command line tool
-----------------

After installation, you should have ``currency_converter`` in your ``$PATH``:

.. code-block:: bash

 $ currency_converter 100 USD --to EUR
 100.000 USD = 87.512 EUR on 2016-05-06

Python API
----------

Create once the currency converter object:

.. code-block:: python

    >>> from currency_converter import CurrencyConverter
    >>> c = CurrencyConverter()

Convert from ``EUR`` to ``USD`` using the last available rate:

.. code-block:: python

    >>> c.convert(100, 'EUR', 'USD') # doctest: +SKIP
    137.5...

Default target currency is ``EUR``:

.. code-block:: python

    >>> c.convert(100, 'EUR')
    100.0
    >>> c.convert(100, 'USD') # doctest: +SKIP
    72.67...

You can change the date of the rate:

.. code-block:: python

    >>> from datetime import date # datetime works too
    >>> c.convert(100, 'EUR', 'USD', date=date(2013, 3, 21))
    129...

Fallbacks
~~~~~~~~~

Some rates are missing:

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

We also have a fallback mode for dates outside the currency bounds:

.. code-block:: python

    >>> c = CurrencyConverter()
    >>> c.convert(100, 'EUR', 'USD', date=date(1986, 2, 2))
    Traceback (most recent call last):
    RateNotFoundError: 1986-02-02 not in USD bounds 1999-01-04/2016-04-29
    >>> 
    >>> c = CurrencyConverter(fallback_on_wrong_date=True)
    >>> c.convert(100, 'EUR', 'USD', date=date(1986, 2, 2)) # fallback to 1999-01-04
    117.89...

Other attributes
~~~~~~~~~~~~~~~~

+ ``bounds`` lets you know the first and last available date for each currency

.. code-block:: python

    >>> first_date, last_date = c.bounds['USD']
    >>> first_date
    datetime.date(1999, 1, 4)
    >>> last_date
    datetime.date(2016, 5, 6)

+ ``currencies`` is a set containing all available currencies

.. code-block:: python

    >>> c.currencies # doctest: +SKIP
    set(['SGD', 'CAD', 'SEK', 'GBP', ...
    >>> 'AAA' in c.currencies
    False
    >>> c.convert(100, 'AAA')
    Traceback (most recent call last):
    ValueError: AAA is not a supported currency

Finally, you can use your own currency file, as long as it has the same format (ECB):

.. code-block:: python

    >>> c = CurrencyConverter('./path/to/currency/file.csv') # doctest: +SKIP

