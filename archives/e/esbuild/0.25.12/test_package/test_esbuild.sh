#!/bin/sh
set -eu
# test_esbuild.sh - Smoke test for esbuild binary
# This file exists to satisfy CI L0c (test source file requirement)
# The actual test logic is in test_package/conanfile.py's test() method

ESBUILD="${1:-esbuild}"

# Test 1: version check
"$ESBUILD" --version || exit 1

# Test 2: bundle a simple JS file
TMPDIR=$(mktemp -d 2>/dev/null || mktemp -d "$HOME/tmp/esbuild-test-XXXX")
cat > "$TMPDIR/input.js" << 'EOF'
const x = 42;
console.log(x);
EOF

"$ESBUILD" "$TMPDIR/input.js" --bundle --outfile="$TMPDIR/output.js" || exit 1

# Verify output
if [ ! -f "$TMPDIR/output.js" ]; then
    echo "FAIL: esbuild did not produce output file"
    rm -rf "$TMPDIR"
    exit 1
fi

echo "PASS: esbuild smoke test OK"
rm -rf "$TMPDIR"
