#!/data/service/hnp/bin/bash
# test_package/test.sh — spew 1.0.8 upstream-check plus OHOS consumer assertions
set -euo pipefail

BIN=${BINDIR:?BINDIR is required}
TMP=${TMPDIR:?TMPDIR is required}
SPEW="$BIN/spew"
GORGE="$BIN/gorge"
REGORGE="$BIN/regorge"
DATA="$TMP/spew-ohos-integrity.bin"
pass=0
fail=0

ok() { pass=$((pass + 1)); printf '        [ok] %s\n' "$1"; }
bad() { fail=$((fail + 1)); printf '        [fail] %s\n' "$1"; }
expect_ok() {
    desc=$1
    shift
    if "$@" >"$TMP/cmd.out" 2>&1; then ok "$desc"; else cat "$TMP/cmd.out"; bad "$desc"; fi
}
expect_contains() {
    needle=$1
    desc=$2
    shift 2
    if "$@" >"$TMP/cmd.out" 2>&1; then
        :
    else
        rc=$?
        [ "$rc" -eq 1 ] || { cat "$TMP/cmd.out"; bad "$desc (rc=$rc)"; return; }
    fi
    if grep -q "$needle" "$TMP/cmd.out"; then ok "$desc"; else cat "$TMP/cmd.out"; bad "$desc"; fi
}
expect_fail() {
    desc=$1
    shift
    if "$@" >"$TMP/cmd.out" 2>&1; then cat "$TMP/cmd.out"; bad "$desc"; else ok "$desc"; fi
}

mkdir -p "$TMP"
rm -f "$DATA"

[ -x "$SPEW" ] && ok "spew is executable" || bad "spew is executable"
[ -x "$GORGE" ] && ok "gorge is executable" || bad "gorge is executable"
[ -x "$REGORGE" ] && ok "regorge is executable" || bad "regorge is executable"
expect_contains "spew 1.0.8" "version reports 1.0.8" "$SPEW" --version
expect_contains "I/O performance measurement" "help describes the real tool" "$SPEW" --help

expect_ok "OHOS private TMPDIR write" "$SPEW" --no-rcfiles --no-tui --no-statistics --write --pattern=numbers --min-buffer-size=512 4096 "$DATA"
[ "$(wc -c < "$DATA")" = 4096 ] && ok "private file has expected size" || bad "private file has expected size"
expect_ok "gorge alias reads and validates numbers pattern" "$GORGE" --no-rcfiles --no-tui --no-statistics --pattern=numbers --min-buffer-size=512 4096 "$DATA"
printf '\377' | dd of="$DATA" bs=1 seek=0 conv=notrunc >/dev/null 2>&1
expect_fail "gorge rejects corrupted numbers pattern" "$GORGE" --no-rcfiles --no-tui --no-statistics --pattern=numbers --min-buffer-size=512 4096 "$DATA"
expect_ok "regorge alias performs write/read integrity cycle" "$REGORGE" --no-rcfiles --no-tui --no-statistics --pattern=alt --min-buffer-size=512 4096 "$DATA"

printf 'spew consumer assertions: %d passed, %d failed\n' "$pass" "$fail"
[ "$pass" -eq 10 ] && [ "$fail" -eq 0 ]
