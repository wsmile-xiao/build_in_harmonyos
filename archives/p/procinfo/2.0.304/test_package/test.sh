#!/data/service/hnp/bin/bash
# Consumer smoke test for procinfo/2.0.304.
#
# Modes exercised (all non-fullscreen; no tty/TERM required):
#   1. `procinfo -v`  -> prints "procinfo version 2.0", exit 0
#   2. `procinfo -h`  -> prints usage, exit 0
#   3. `procinfo` with stdin at EOF -> one-shot report (interval==0 breaks
#      after a single mainLoop), exit 0. On hardened systems (OHOS policy
#      denies /proc/interrupts, /proc/diskstats, /sys/class/net) the patched
#      binary must still render the readable sections (memory/CPU/loadavg)
#      and exit 0 instead of aborting.

set -e
set -o pipefail

BIN="$(command -v procinfo)"
echo "bin: $BIN"
test -n "$BIN" && test -x "$BIN"
echo "== [1/3] procinfo -v"
V_OUT="$("$BIN" -v)"
echo "$V_OUT"
echo "$V_OUT" | grep -q "procinfo version"

echo "== [2/3] procinfo -h"
H_OUT="$("$BIN" -h)"
echo "$H_OUT" | head -2
echo "$H_OUT" | grep -q "usage:"

echo "== [3/3] one-shot report (stdin=/dev/null)"
# write to a temp path so the recipe source dir stays clean (no run artifacts)
OUT_FILE="$(mktemp 2>/dev/null || echo ./procinfo_smoke_out_tmp.txt)"
ERR_FILE="$(mktemp 2>/dev/null || echo ./procinfo_smoke_err_tmp.txt)"
"$BIN" < /dev/null > "$OUT_FILE" 2> "$ERR_FILE"
RC=$?
echo "exit=$RC, lines=$(wc -l < "$OUT_FILE")"
test "$RC" -eq 0
test "$(wc -l < "$OUT_FILE")" -ge 5
grep -q "Memory:" "$OUT_FILE"
grep -q "Load average:" "$OUT_FILE"
head -8 "$OUT_FILE"
rm -f "$OUT_FILE" "$ERR_FILE"
echo "PASS: procinfo consumer smoke (8 assertions)"
