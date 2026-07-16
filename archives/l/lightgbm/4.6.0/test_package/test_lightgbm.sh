#!/bin/sh
set -eu
lightgbm --help >/dev/null 2>&1 || test "$?" -eq 255
