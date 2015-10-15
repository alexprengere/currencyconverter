from collections import defaultdict
from datetime import datetime

from currency_converter import (CurrencyConverter, DATE_FORMAT, DELIMITER,
                                NA_VALUES, REF_CURRENCY)


class S3CurrencyConverter(CurrencyConverter):
    """
    Load the ECB CSV file from an S3 key instead of from a local file.

    The first argument should be an instance of boto.s3.key.Key (or any other
    object that provides a get_contents_as_string() method which returns the
    CSV file as a string).
    """
    def __init__(self, currency_file, **kwargs):
        """ Make currency_file a required attribute """
        super(S3CurrencyConverter, self).__init__(currency_file, **kwargs)

    def _load_file(self, currency_file):
        self._rates = defaultdict(dict)
        self.currencies = set()

        f = currency_file.get_contents_as_string()
        lines = f.splitlines()

        header = lines.pop(0)
        currencies = header.strip().split(DELIMITER)[1:]

        for currency in currencies:
            if currency:
                self.currencies.add(currency)
        self.currencies.add(REF_CURRENCY)

        for line in lines:
            line = line.strip().split(DELIMITER)
            date = datetime.strptime(line[0], DATE_FORMAT)
            rates = line[1:]

            for currency, rate in zip(currencies, rates):
                if currency:
                    if rate in NA_VALUES:
                        self._rates[date][currency] = None
                    else:
                        self._rates[date][currency] = float(rate)

        self.dates = set(self._rates)
        self.first_date = min(self.dates)
        self.last_date = max(self.dates)
