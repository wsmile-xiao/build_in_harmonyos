#!/bin/sh
# le 1.16.8 consumer test — exercises the installed editor binary.
#
# Usage: test_le.sh <le-binary>
#
# le is an interactive TUI editor, so an unattended test can only drive its
# non-interactive entry points.  --help is covered on purpose: upstream prints
# the usage text and exits 1 on that path, so the exit code is itself part of
# the assertion (also recorded in notes.md).  Every dump is written to the
# current (build) folder — never into the package or the recipe tree.
set -u

BIN="${1:?usage: test_le.sh <le-binary>}"
DUMP="le-consumer-dump.txt"

pass=0
fail=0
ok() { pass=$((pass + 1)); echo "ok - $1"; }
no() { fail=$((fail + 1)); echo "NOT OK - $1"; }

# assert_out <needle> <desc> <args...>   (expects rc=0)
assert_out() {
    needle="$1"; desc="$2"; shift 2
    out=$("$BIN" "$@" < /dev/null 2>&1); rc=$?
    if [ "$rc" -eq 0 ] && echo "$out" | grep -q -- "$needle"; then
        ok "$desc"
    else
        no "$desc (needle='$needle', rc=$rc)"
        echo "$out" | head -3 | sed 's/^/    /'
    fi
}

# assert_min_lines <n> <desc> <args...>   (expects rc=0)
assert_min_lines() {
    want="$1"; desc="$2"; shift 2
    "$BIN" "$@" < /dev/null > "$DUMP" 2>&1; rc=$?
    lines=$(wc -l < "$DUMP" | tr -d ' ')
    if [ "$rc" -eq 0 ] && [ "$lines" -ge "$want" ]; then
        ok "$desc ($lines lines)"
    else
        no "$desc (expected >= $want lines at rc=0, got $lines lines, rc=$rc)"
    fi
}

# assert_rc <expected-rc> <needle> <desc> <args...>
assert_rc() {
    want="$1"; needle="$2"; desc="$3"; shift 3
    out=$("$BIN" "$@" < /dev/null 2>&1); rc=$?
    if [ "$rc" -eq "$want" ] && echo "$out" | grep -q -- "$needle"; then
        ok "$desc (rc=$rc)"
    else
        no "$desc (expected rc=$want with '$needle', got rc=$rc)"
        echo "$out" | head -3 | sed 's/^/    /'
    fi
}

assert_out "1.16.8"          "--version reports upstream version 1.16.8" --version
assert_out "Text editor LE"  "--version identifies the LE editor" --version
assert_out "backward-char"   "--dump-keymap exports the default keymap" --dump-keymap
assert_min_lines 100         "--dump-keymap export is complete" --dump-keymap
assert_out "default_colors"  "--dump-colors exports the colour table" --dump-colors
assert_min_lines 20          "--dump-colors export is complete" --dump-colors
assert_rc 1 "Usage: le"      "--help prints usage on the upstream exit-1 path" --help

rm -f "$DUMP" 2>/dev/null || true

echo "LE_CONSUMER_CHECKS=$((pass + fail)) FAILURES=$fail"
[ "$fail" -eq 0 ] || exit 1
echo "LE_CONSUMER_OK"
