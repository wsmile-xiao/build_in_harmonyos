#!/bin/sh
set -euo pipefail
lightgbm --help >/dev/null 2>&1 || test "$?" -eq 255
