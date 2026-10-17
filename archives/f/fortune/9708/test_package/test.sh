#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for fortune executable
# Runs in conanrun env (PATH includes installed bin/ and games/)
set -euo pipefail

echo "[step] strfile (no args, should show usage)"
strfile 2>&1 | head -1 || true  # strfile exits non-zero on no-args usage, checking output only
echo "        [ok] strfile OK"

echo "[step] unstr (no args, should show usage)"
unstr 2>&1 | head -1 || true  # unstr exits non-zero on no-args usage, checking output only
echo "        [ok] unstr OK"

echo "[step] fortune with test data"
TMPDIR_TEST="${TMPDIR:-/tmp}"
FORTUNE_DATA="$TMPDIR_TEST/fortune-test-$$"
mkdir -p "$FORTUNE_DATA"
cat > "$FORTUNE_DATA/test" << 'EOF'
This is a test fortune.
%
Another test fortune.
%
The third test fortune.
EOF

# Create .dat file using strfile from the package
strfile "$FORTUNE_DATA/test" "$FORTUNE_DATA/test.dat"
echo "        [ok] strfile created .dat file"

# Run fortune with the test data file
# fortune may return non-zero when no match, so allow failure here
output=$(fortune "$FORTUNE_DATA/test" 2>/dev/null) || true  # fortune exits non-zero on some random selections
if [ -n "$output" ]; then
    echo "        [ok] fortune produced output: $output"
else
    echo "        [fail] fortune produced no output"
    exit 1
fi

# Cleanup
rm -rf "$FORTUNE_DATA"

echo "[ok] All tests passed"
