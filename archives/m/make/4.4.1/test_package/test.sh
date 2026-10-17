#!/bin/sh
set -eu

make --version > version.txt
make -f smoke.mk clean all > output.txt
cp out.txt recipe-output.txt
make -f smoke.mk clean > /dev/null
test ! -e out.txt
