#!/bin/sh
set -eu

m4 --version >/dev/null
m4 test.m4 > output.txt
