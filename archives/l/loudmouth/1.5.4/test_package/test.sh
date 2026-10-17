#!/bin/sh
#
# Wrapper for the loudmouth consumer smoke test.
#
# On OHOS the plain test binary is executed through the injected /bin/sh
# (toybox ash, whose getcwd works on HMDFS) rather than the HNP bash, per the
# HMBS platform diagnostic [shell_getcwd]. The first argument is the absolute
# path to the compiled test binary and the second is the path where the
# binary writes its authoritative counts JSON.
set -e

EXE="$1"
RESULT_FILE="$2"

"$EXE" "$RESULT_FILE"
