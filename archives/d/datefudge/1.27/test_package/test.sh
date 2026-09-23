#!/usr/bin/env bash
# Consumer and upstream-derived functional checks for datefudge.

set -euo pipefail

package_folder=$1
test_executable=$2
mode=$3
datefudge="$package_folder/bin/datefudge"
library="$package_folder/lib/datefudge/datefudge.so"

[ -x "$datefudge" ]
[ -f "$library" ]
if grep -q '@VERSION@\|@LIBDIR@\|@MULTIARCH_PATTERN@' "$datefudge"; then
  echo "[fail] generated launcher still contains template placeholders" >&2
  exit 1
fi
"$datefudge" --version | grep -F "Version 1.27"
"$datefudge" --help | grep -F "Usage:"

if [ "$mode" = "inspect" ]; then
  echo "[ok] package layout, relocatable launcher, version, and help checks passed"
  exit 0
fi

export TZ=UTC
expected_epoch=1700000000
DATEFUDGE="$expected_epoch" DATEFUDGE_DOSTATIC=1 DATEFUDGE_EXPECTED="$expected_epoch" \
  LD_PRELOAD="$library" "$test_executable"

actual=$("$datefudge" -s "2019-07-31 23:01:12 UTC" date '+%F %T')
[ "$actual" = "2019-07-31 23:01:12" ]

actual=$("$datefudge" "2019-07-31 23:01:12 UTC" bash -c 'sleep 1; date "+%F %T"')
[ "$actual" = "2019-07-31 23:01:13" ]

actual=$("$datefudge" -s "2019-07-31 23:01:12 UTC" bash -c 'sleep 1; date "+%F %T"')
[ "$actual" = "2019-07-31 23:01:12" ]

actual=$("$datefudge" -s "2024-01-02 18:03:04.56789 UTC" \
  bash -c 'sleep 1; date "+%T %N"')
[ "$actual" = "18:03:04 000000000" ]

actual=$("$datefudge" "2020-02-29 01:02:03 UTC" date '+%a %b %d %T %Y')
[ "$actual" = "Sat Feb 29 01:02:03 2020" ]

# The nested shell, rather than this test driver, must expand LD_PRELOAD.
# shellcheck disable=SC2016
actual=$(env -u LD_PRELOAD "$datefudge" now bash -c 'printf "%s" "$LD_PRELOAD"')
[ "$actual" = "datefudge.so" ]

# shellcheck disable=SC2016
actual=$(env -u LD_PRELOAD "$datefudge" -l "$library" now \
  bash -c 'printf "%s" "$LD_PRELOAD"')
[ "$actual" = "$library:datefudge.so" ]

echo "[ok] datefudge functional test matrix passed"
