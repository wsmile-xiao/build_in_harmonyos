#!/usr/bin/env bash
set -eu
: "${UNITS_DATA_DIR:?UNITS_DATA_DIR is not set}"
command -v units >/dev/null
result="$(units -t '2 m' cm)"
test "$result" = "200"
result="$(units -t '1 kg' g)"
test "$result" = "1000"
result="$(units -t '1 hour' s)"
test "$result" = "3600"
result="$(units -t '1 inch' cm)"
test "$(printf '%s' "$result" | cut -c1-7)" = "2.54"
result="$(units -t '1 m^2' cm^2)"
test "$result" = "10000"
if units -t '1 not_a_unit' m >/dev/null 2>&1; then
  echo 'invalid unit unexpectedly accepted' >&2
  exit 1
fi
test -s "$UNITS_DATA_DIR/definitions.units"
test -s "$UNITS_DATA_DIR/elements.units"
echo 'units smoke: 8 assertions passed'
