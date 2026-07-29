#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for GNU sed 4.9
# Uses absolute SED_BIN from conanrun env to ensure the PACKAGED binary
# is tested (not system toybox sed).
set -euo pipefail

# SED_BIN must be set by test_package/conanfile.py
SED="${SED_BIN:?SED_BIN not set — test_package/conanfile.py must export it}"

echo ""
echo "=== GNU sed 4.9 test_package ==="
echo "[info] Using: $SED"

# T1: version check — must be GNU sed, not toybox
echo "[T1] sed --version (GNU check)"
version_out=$("$SED" --version 2>&1) || {
    echo "❌ T1 FAIL: sed --version failed"
    exit 1
}
echo "$version_out" | head -1
if echo "$version_out" | grep -q "GNU sed"; then
    echo "✅ T1 PASS (GNU sed confirmed)"
else
    echo "❌ T1 FAIL: not GNU sed (got: $(echo "$version_out" | head -1))"
    exit 1
fi

# T2: basic substitution
echo "[T2] basic s/// substitution"
result=$(echo "hello world" | "$SED" 's/world/sed/')
if [ "$result" = "hello sed" ]; then
    echo "✅ T2 PASS (got: $result)"
else
    echo "❌ T2 FAIL: expected 'hello sed', got '$result'"
    exit 1
fi

# T3: global substitution
echo "[T3] global s///g"
result=$(echo "a,b,c" | "$SED" 's/,/:/g')
if [ "$result" = "a:b:c" ]; then
    echo "✅ T3 PASS (got: $result)"
else
    echo "❌ T3 FAIL: expected 'a:b:c', got '$result'"
    exit 1
fi

# T4: extended regex -E
echo "[T4] extended regex -E"
result=$(echo "abc123def" | "$SED" -E 's/[0-9]+/NUM/')
if [ "$result" = "abcNUMdef" ]; then
    echo "✅ T4 PASS (got: $result)"
else
    echo "❌ T4 FAIL: expected 'abcNUMdef', got '$result'"
    exit 1
fi

# T5: in-place editing via temp file (TMPDIR workaround)
echo "[T5] in-place edit -i"
tmpdir="${TMPDIR:-/tmp}"
test -w "$tmpdir" || tmpdir="$HOME/tmp"
mkdir -p "$tmpdir"
tf=$(mktemp "$tmpdir/sed-test-XXXXXX")
echo "before" > "$tf"
"$SED" -i 's/before/after/' "$tf"
result=$(cat "$tf")
rm -f "$tf"
if [ "$result" = "after" ]; then
    echo "✅ T5 PASS (got: $result)"
else
    echo "❌ T5 FAIL: expected 'after', got '$result'"
    exit 1
fi

echo ""
echo "=== All test_package tests PASSED ==="
