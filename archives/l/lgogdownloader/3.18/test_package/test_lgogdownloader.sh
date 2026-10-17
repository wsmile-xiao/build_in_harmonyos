#!/usr/bin/env bash
# test_package/test_lgogdownloader.sh
# Consumer smoke test for the lgogdownloader CLI (upstream-equivalent checks:
# the upstream GitHub Actions "linux" workflow only runs `./lgogdownloader --help`).
set -euo pipefail

BIN="$1"
WORK="$2"
LOG="${3:-}"

if [ -z "${BIN:-}" ] || [ -z "${WORK:-}" ]; then
    echo "Usage: $0 <lgogdownloader_binary> <work_dir> [log_file]"
    exit 1
fi

mkdir -p "$WORK"
LOG="${LOG:-$WORK/test_lgogdownloader.log}"

{
echo "=== lgogdownloader consumer test, $(date -Is) ==="
echo "binary: $BIN"
[ -x "$BIN" ] || { echo "FAIL: binary not executable"; exit 1; }

fail=0

echo
echo "--- Test 1: --version reports the exact upstream version ---"
rc=0
out=$("$BIN" --version) || rc=$?
echo "stdout: $out"
echo "exit=$rc"
if [ $rc -ne 0 ]; then echo "FAIL: --version exit=$rc"; fail=1; fi
if [ "$out" != "LGOGDownloader 3.18" ]; then
    echo "FAIL: unexpected version string '$out'"
    fail=1
else
    echo "PASS: version string OK"
fi

echo
echo "--- Test 2: --help lists the documented CLI surface ---"
rc=0
help=$("$BIN" --help) || rc=$?
echo "help lines: $(printf '%s\n' "$help" | wc -l)"
echo "exit=$rc"
if [ $rc -ne 0 ]; then echo "FAIL: --help exit=$rc"; fail=1; fi
for opt in "--login" "--download" "--list" "--repair" "--game"; do
    if printf '%s\n' "$help" | grep -q -- "$opt"; then
        echo "PASS: --help documents $opt"
    else
        echo "FAIL: --help missing $opt"
        fail=1
    fi
done

echo
echo "--- Test 3: unknown option is rejected (exit != 0) ---"
rc=0
"$BIN" --definitely-not-a-real-option >/dev/null 2>&1 || rc=$?
echo "exit=$rc"
if [ $rc -eq 0 ]; then
    echo "FAIL: unknown option accepted (exit 0)"
    fail=1
else
    echo "PASS: unknown option rejected with exit=$rc"
fi

echo
if [ $fail -ne 0 ]; then
    echo "=== lgogdownloader consumer test FAILED ==="
    exit 1
fi
echo "=== lgogdownloader consumer test PASSED ==="
} 2>&1 | tee "$LOG"

exit "${PIPESTATUS[0]}"
