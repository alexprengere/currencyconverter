#!/usr/bin/env python

from itertools import zip_longest

from .currency_converter import CurrencyConverter, CURRENCY_FILE, parse_date
from ._version import __version__


def grouper(iterable, n, fillvalue=None):
    """Group iterable by n elements.

    >>> for t in grouper('abcdefg', 3, fillvalue='x'):
    ...     print(''.join(t))
    abc
    def
    gxx
    """
    return list(zip_longest(*[iter(iterable)] * n, fillvalue=fillvalue))


def main():
    import argparse

    parser = argparse.ArgumentParser(prog="currency_converter")
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s, version {__version__}",
    )
    parser.add_argument("amount", type=float)
    parser.add_argument("currency")

    parser.add_argument(
        "-t",
        "--to",
        help="target currency, default is %(default)s",
        default="EUR",
    )

    parser.add_argument(
        "-d",
        "--date",
        help="date of rate, with format %%Y-%%m-%%d",
        default=None,
    )

    parser.add_argument(
        "-v",
        "--verbose",
        help=(
            "display available currencies, use twice (-vv) to "
            "also display details of missing rates completion"
        ),
        action="count",
        default=0,
    )

    parser.add_argument(
        "--decimal",
        help="use decimal.Decimal internally",
        action="store_true",
    )

    parser.add_argument(
        "-f",
        "--file",
        help="change currency file used, default is %(default)s",
        default=CURRENCY_FILE,
    )

    args = parser.parse_args()

    c = CurrencyConverter(
        currency_file=args.file,
        fallback_on_wrong_date=True,
        fallback_on_missing_rate=True,
        decimal=args.decimal,
        verbose=args.verbose > 1,
    )
    currencies = sorted(c.currencies)

    if args.verbose:
        print(f"{len(currencies)} available currencies:")
        for group in grouper(currencies, 10, fillvalue=""):
            print(" ".join(group))
        print("")

        currencies.sort(key=lambda u: c.bounds[u].last_date, reverse=True)
        currencies.sort(key=lambda u: c.bounds[u].first_date)
        for currency in currencies:
            first_date, last_date = c.bounds[currency]
            print(
                "{}: from {} to {} ({} days)".format(
                    currency, first_date, last_date, 1 + (last_date - first_date).days
                )
            )
        print("")

    if args.currency not in c.currencies:
        print(rf'/!\ "{args.currency}" is not in available currencies:')
        for group in grouper(currencies, 10, fillvalue=""):
            print(" ".join(group))
        exit(1)

    if args.date is not None:
        date = parse_date(args.date)
    else:
        date = c.bounds[args.currency].last_date

    new_amount = c.convert(
        amount=args.amount,
        currency=args.currency,
        new_currency=args.to,
        date=date,
    )

    print(
        "{:,.3f} {} = {:,.3f} {} on {}".format(
            args.amount, args.currency, new_amount, args.to, date
        )
    )


if __name__ == "__main__":
    main()
