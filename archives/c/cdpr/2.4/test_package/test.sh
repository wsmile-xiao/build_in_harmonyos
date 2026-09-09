#!/data/service/hnp/bin/bash
# test_package/test.sh — functional smoke test for the cdpr executable.
# Runs inside the conanrun env (PATH includes the installed bin/).
# NOTE: never run a bare `cdpr` here — without -h it blocks up to 300s
# waiting for a CDP packet. `cdpr -h` prints the banner + usage and exits 0.
set -euo pipefail

OUT="${TMPDIR:-$HOME/tmp}/cdpr-h-$$.txt"
mkdir -p "$(dirname "$OUT")"
trap 'rm -f "$OUT"' EXIT

# Test 1: binary executes, exits 0, output is non-empty
echo "[test] cdpr -h (exit code + non-empty output)"
cdpr -h > "$OUT" 2>&1
test -s "$OUT" || {
    echo "FAIL: cdpr -h produced empty output"
    exit 1
}
echo "PASS: cdpr -h exited 0 with non-empty output"

# Test 2: startup banner reports the product and Version 2.4
echo "[test] banner (product + Version 2.4)"
grep -q "Cisco Discovery Protocol Reporter" "$OUT" || {
    echo "FAIL: banner missing product name"
    exit 1
}
grep -q "Version 2.4" "$OUT" || {
    echo "FAIL: banner missing Version 2.4"
    exit 1
}
echo "PASS: banner OK"

# Test 3: usage text documents the device option and help marker
echo "[test] usage (device option + help marker)"
grep -q "Specify device" "$OUT" || {
    echo "FAIL: usage missing device option text"
    exit 1
}
grep -qi "Print this usage" "$OUT" || {
    echo "FAIL: usage missing help marker"
    exit 1
}
echo "PASS: usage OK"
