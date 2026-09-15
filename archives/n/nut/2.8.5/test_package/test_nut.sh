#!/bin/sh
set -euo pipefail

UPSC="$(command -v upsc)"
test -x "$UPSC"

"$UPSC" -V > nut-version.txt
grep -F "Network UPS Tools upsc 2.8.5" nut-version.txt

"$UPSC" -h > nut-help.txt
grep -F "usage:" nut-help.txt

UPSD="$(command -v upsd)"
test -x "$UPSD"

"$UPSD" --version > nutd-version.txt
grep -F "Network UPS Tools upsd 2.8.5" nutd-version.txt
