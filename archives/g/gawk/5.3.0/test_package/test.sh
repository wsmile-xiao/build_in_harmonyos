#!/usr/bin/env bash
# test_package/test.sh — smoke test for gawk executable
# Uses absolute GAWK_BIN from conanrun env to ensure the PACKAGED binary
# is tested (not system awk).
set -euo pipefail

# GAWK_BIN must be set by test_package/conanfile.py
GAWK="${GAWK_BIN:?GAWK_BIN not set — test_package/conanfile.py must export it}"

echo ""
echo "=== GNU gawk 5.3.0 test_package ==="
echo "[info] Using: $GAWK"

# T1: Version check — must be GNU awk, not toybox
echo "[T1] gawk --version (GNU check)"
version_out=$("$GAWK" --version 2>&1) || {
    echo "FAIL: gawk --version failed"
    exit 1
}
echo "$version_out" | head -1
if echo "$version_out" | grep -q "GNU Awk"; then
    echo "T1 PASS (GNU Awk confirmed)"
else
    echo "T1 FAIL: not GNU Awk (got: $(echo "$version_out" | head -1))"
    exit 1
fi

# T2: Arithmetic: 1+2*3 should equal 7
echo "[T2] arithmetic (1+2*3==7)"
"$GAWK" 'BEGIN {exit (1+2*3==7) ? 0 : 1}' || { echo "FAIL: arithmetic"; exit 1; }
echo "T2 PASS"

# T3: Field extraction: \$1 of "hello world" should be "hello"
echo "[T3] field extraction"
"$GAWK" '{exit ($1=="hello") ? 0 : 1}' <<< "hello world" || { echo "FAIL: field extraction"; exit 1; }
echo "T3 PASS"

echo ""
echo "=== All gawk smoke tests PASSED ==="
