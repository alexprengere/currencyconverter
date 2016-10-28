#!/usr/bin/env bash

DIRNAME=`dirname $0`
cd "$DIRNAME/currency_converter"

rm -f eurofxref-hist.zip
wget 'http://www.ecb.int/stats/eurofxref/eurofxref-hist.zip'
