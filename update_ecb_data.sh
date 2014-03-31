#!/usr/bin/env bash

DIRNAME=`dirname $0`
cd $DIRNAME

rm -f eurofxref-hist.zip eurofxref-hist.csv
wget 'http://www.ecb.int/stats/eurofxref/eurofxref-hist.zip'

unzip eurofxref-hist.zip
rm -f eurofxref-hist.zip

