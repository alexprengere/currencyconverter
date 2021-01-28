#!/usr/bin/env bash

DIRNAME=`dirname $0`
cd "$DIRNAME/currency_converter"

rm -f eurofxref-hist.zip
wget 'https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.zip'
