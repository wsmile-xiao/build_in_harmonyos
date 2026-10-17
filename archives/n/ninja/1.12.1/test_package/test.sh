#!/data/service/hnp/bin/bash
# Test script for ninja 1.12.1 conan package
# Runs the ninja binary and verifies its output
set -e

# Get the ninja binary path from the first argument or PATH
NINJA_BIN="${1:-ninja}"

# Test 1: Version check
echo "Test 1: ninja --version"
VERSION=$("$NINJA_BIN" --version)
if [ "$VERSION" != "1.12.1" ]; then
    echo "FAIL: Expected version 1.12.1, got $VERSION"
    exit 1
fi
echo "PASS: version is 1.12.1"

# Test 2: Build a simple target
echo "Test 2: Build simple target"
TMPDIR_TEST="${TMPDIR:-/tmp}/ninja_test_$$"
mkdir -p "$TMPDIR_TEST"
cd "$TMPDIR_TEST"
cat > build.ninja << 'EOF'
rule echo
  command = echo hello-from-ninja

build hello: echo
EOF
OUTPUT=$("$NINJA_BIN" hello 2>&1)
if [ "$OUTPUT" != "hello-from-ninja" ]; then
    echo "FAIL: Expected 'hello-from-ninja', got '$OUTPUT'"
    rm -rf "$TMPDIR_TEST"
    exit 1
fi
echo "PASS: build target works"
rm -rf "$TMPDIR_TEST"

echo "All tests passed"
