.. image:: https://raw.githubusercontent.com/alexprengere/currencyconverter/master/logo/cc3.png

|actions|_ |cratev|_ |crated|_

.. _actions : https://github.com/alexprengere/currencyconverter/actions/workflows/python-package.yml
.. |actions| image:: https://github.com/alexprengere/currencyconverter/actions/workflows/python-package.yml/badge.svg

.. _cratev : https://pypi.org/project/CurrencyConverter/
.. |cratev| image:: https://img.shields.io/pypi/v/currencyconverter.svg

.. _crated : https://pypi.org/project/CurrencyConverter/
.. |crated| image:: https://static.pepy.tech/badge/currencyconverter

This is a currency converter that uses historical rates against a reference currency (Euro).

Currency data sources
---------------------

The default source is the `European Central Bank <https://www.ecb.europa.eu>`_. This is the ECB historical rates for 42 currencies against the Euro since 1999.
It can be downloaded here: `eurofxref-hist.zip <https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.zip>`_.
The converter can use different sources as long as the format is the same.

Note that the currency converter does not query the API in real time, to avoid the overhead of the HTTP request. It uses embedded data in the library, which might not be up to date.
If you need the latest data, please refer to the *data* section.

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

Data
~~~~

You can use your own currency file, as long as it has the same format (ECB):

.. code-block:: python

    from currency_converter import ECB_URL, SINGLE_DAY_ECB_URL

    # Load the packaged data (might not be up to date)
    c = CurrencyConverter()

    # Download the full history, this will be up to date. Current value is:
    # https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.zip
    c = CurrencyConverter(ECB_URL)

    # Dowload only the latest available day. Current value is:
    # https://www.ecb.europa.eu/stats/eurofxref/eurofxref.zip
    c = CurrencyConverter(SINGLE_DAY_ECB_URL)

    # Load your custom file
    c = CurrencyConverter('./path/to/currency/file.csv')

Since the raw data is updated only once a day, it might be better to only download it once a day:

.. code-block:: python

    import os.path as op
    import urllib.request
    from datetime import date

    from currency_converter import ECB_URL, CurrencyConverter

    filename = f"ecb_{date.today():%Y%m%d}.zip"
    if not op.isfile(filename):
        urllib.request.urlretrieve(ECB_URL, filename)
    c = CurrencyConverter(filename)

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

The fallback method can be configured with the ``fallback_on_missing_rate_method`` parameter, which currently supports ``"linear_interpolation"`` and ``"last_known"`` values.

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

Decimal
~~~~~~~

If you need exact conversions, you can use the ``decimal`` option to use ``decimal.Decimal`` internally when parsing rates.
This will slow down the load time by a factor 10 though.

.. code-block:: python

    >>> c = CurrencyConverter(decimal=True)
    >>> c.convert(100, 'EUR', 'USD', date=date(2013, 3, 21))
    Decimal('129.100')

Other attributes
~~~~~~~~~~~~~~~~

+ ``bounds`` lets you know the first and last available date for each currency

.. code-block:: python

    >>> first_date, last_date = c.bounds['USD']
    >>> first_date
    datetime.date(1999, 1, 4)
    >>> last_date # doctest: +SKIP
    datetime.date(2016, 11, 14)

+ ``currencies`` is a set containing all available currencies

.. code-block:: python

    >>> c.currencies # doctest: +SKIP
    set(['SGD', 'CAD', 'SEK', 'GBP', ...
    >>> 'AAA' in c.currencies
    False
    >>> c.convert(100, 'AAA')
    Traceback (most recent call last):
    ValueError: AAA is not a supported currency
