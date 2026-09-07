#!/usr/bin/env bash
# R34: real functional test for cern-ndiff 5.09.03 — exercises the packaged
# ndiff binary. Cases mirror the Homebrew cern-ndiff formula test block plus
# one out-of-tolerance case asserting the upstream "diffs detected" report.
set -u

BIN_DIR="${1:?usage: test_ndiff.sh <package bin dir>}"

FAIL=0

# Check 1/3: ndiff exists and is executable
NDIFF="$BIN_DIR/ndiff"
if [ ! -x "$NDIFF" ]; then
    echo "FAIL: ndiff missing or not executable in $BIN_DIR"
    FAIL=1
else
    echo "[ok] check 1/3: ndiff binary present and executable"
fi

# Check 2/3: in-tolerance pair (Homebrew smoke case) must exit 0
printf '0.0 2e-3 0.003' > lhs.txt
printf '1e-7 0.002 0.003' > rhs.txt
printf '*   * abs=1e-6' > test.cfg
if [ "$FAIL" -eq 0 ] && "$NDIFF" lhs.txt rhs.txt test.cfg > ndiff_tolerant.log 2>&1; then
    echo "[ok] check 2/3: in-tolerance comparison exits 0"
else
    echo "FAIL: in-tolerance comparison failed (exit=$?)"
    cat ndiff_tolerant.log 2>/dev/null
    FAIL=1
fi

# Check 3/3: out-of-tolerance pair must report diffs detected
printf '1.0' > lhs2.txt
printf '2.0' > rhs2.txt
printf '*   * abs=1e-6' > test2.cfg
# ndiff may exit non-zero when diffs are found, so guard the capture
NDIFF_OUT="$("$NDIFF" lhs2.txt rhs2.txt test2.cfg 2>&1)" || true  # diffs-found exit code is data, not error
if printf '%s' "$NDIFF_OUT" | grep -q "diffs detected"; then
    echo "[ok] check 3/3: out-of-tolerance comparison reports diffs detected"
else
    echo "FAIL: expected 'diffs detected' in ndiff output, got:"
    printf '%s\n' "$NDIFF_OUT"
    FAIL=1
fi

if [ "$FAIL" -eq 0 ]; then
    echo "cern-ndiff test_package: all 3 checks passed"
fi
exit "$FAIL"
