#!/usr/bin/zsh
# test_package/test.sh - verify installed pcal CLI behavior.
set -euo pipefail

bin="${PCAL_BIN:-pcal}"
tmpdir="${TMPDIR:-.}"
ps_out="$tmpdir/pcal-test-$$.ps"
html_out="$tmpdir/pcal-test-$$.html"
cal_out="$tmpdir/pcal-test-$$.calendar"
trap 'rm -f "$ps_out" "$html_out" "$cal_out"' EXIT

"$bin" -v | grep "pcal v4.11.0"

"$bin" -e 9 2026 > "$ps_out"
grep "%%Title: calendar for 09/2026" "$ps_out"

"$bin" -H -e 9 2026 > "$html_out"
grep "<html>" "$html_out"
grep "September 2026" "$html_out"

"$bin" -c 9 2026 > "$cal_out"
grep "opt -A" "$cal_out"
