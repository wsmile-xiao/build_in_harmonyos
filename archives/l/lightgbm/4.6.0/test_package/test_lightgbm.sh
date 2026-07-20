#!/bin/sh
set -eu
(set -o pipefail) 2>/dev/null && set -o pipefail || true
lightgbm --help >/dev/null 2>&1 || test "$?" -eq 255
