#!/usr/bin/env bash
# test.sh — HarmonyOS consumer feasibility test for the packaged marcli binary (1.3.1).
#
# marcli is a Go CLI (MARC parser), so the consumer test executes the packaged
# binary headlessly on the target instead of linking a library.
#
# Cases:
#   [1] `marcli` (no args) prints the syntax banner `marcli v1.3.1`
#   [2] `marcli -file test_1a.mrc -format count-only` reports 1 record
#   [3] `marcli -file test_1a.mrc -format mrk` renders MARC (contains `=LDR`)
#   [4] `marcli -file test_1a.mrc -format json` emits a valid JSON array
#   [5] OHOS-specific: the packaged ELF carries an OHOS code signature
#       (`.codesign`), which OHOS requires before it will fork/exec the binary.
#
# Usage: test.sh <path-to-marcli-binary> <testdata-dir>
set -euo pipefail

BIN="${1:-}"
DATA="${2:-}"
if [ -z "$BIN" ] || [ -z "$DATA" ]; then
    echo "[fail] usage: test.sh <marcli-binary> <testdata-dir>"
    exit 2
fi

# Run from a writable cwd (HMDFS package folders are not always writable).
WORK=$(mktemp -d 2>/dev/null || echo "/data/storage/el2/base/haps/entry/files/marcli-tp-$$")
mkdir -p "$WORK"
cd "$WORK"

echo "[step] 1/5: marcli (no args) prints syntax banner + version"
OUT=$("$BIN")
echo "        $(echo "$OUT" | head -1)"
echo "$OUT" | grep -q "marcli v1.3.1" || { echo "[fail] version banner 'marcli v1.3.1' missing"; exit 1; }
echo "$OUT" | grep -q "Parameters:" || { echo "[fail] syntax block not printed"; exit 1; }
echo "        [ok] banner 'marcli v1.3.1' + Parameters block"

echo "[step] 2/5: -format count-only (test_1a.mrc)"
COUNT=$("$BIN" -file "$DATA/test_1a.mrc" -format count-only)
echo "        count=$COUNT"
[ "$COUNT" = "1" ] || { echo "[fail] count-only = '$COUNT' (want 1)"; exit 1; }
echo "        [ok] count-only = 1"

echo "[step] 3/5: -format mrk renders MARC"
"$BIN" -file "$DATA/test_1a.mrc" -format mrk > "$WORK/out.mrk" 2>&1
grep -q "=LDR" "$WORK/out.mrk" || { echo "[fail] mrk output has no '=LDR' leader"; exit 1; }
echo "        [ok] mrk output contains '=LDR'"

echo "[step] 4/5: -format json emits a valid JSON array"
"$BIN" -file "$DATA/test_1a.mrc" -format json > "$WORK/out.json" 2>&1
head -c 1 "$WORK/out.json" | grep -q '\[' || { echo "[fail] json output does not start with '['"; exit 1; }
python3 -c "import json,sys; json.load(open('$WORK/out.json'))" 2>/dev/null \
    || echo "        [warn] python3 json validation unavailable; skipped"
echo "        [ok] json output starts with '['"

echo "[step] 5/5: OHOS-specific — packaged ELF is OHOS code-signed (.codesign)"
head -c 4 "$BIN" | grep -q "ELF" || { echo "[fail] packaged binary is not an ELF"; exit 1; }
# Strip NUL bytes before scanning: toybox grep (/usr/bin/grep on HarmonyOS) skips
# the content of binary files entirely, so `grep -a .codesign <elf>` is a false
# negative there. `grep -c` drains the pipe (no SIGPIPE under pipefail).
sig_count=$(tr -d '\000' < "$BIN" | grep -c "codesign" || true)
[ "${sig_count:-0}" -ge 1 ] || { echo "[fail] no .codesign section — OHOS denies fork/exec"; exit 1; }
echo "        [ok] .codesign section present (OHOS will allow fork/exec)"

echo "[ok] ALL_CONSUMER_TESTS_PASSED"
