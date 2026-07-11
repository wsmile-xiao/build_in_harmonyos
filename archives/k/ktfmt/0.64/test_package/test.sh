#!/bin/sh
# test_package/test.sh — ktfmt 0.64 L1 smoke test
#
# Called by test_package/conanfile.py test() method.
# Usage: test.sh <ktfmt_binary_path> [work_dir]
#
# Asserts:
#   1. ktfmt --version prints version string
#   2. ktfmt --help prints usage info
#   3. ktfmt --google-style formats a Kotlin file (brace spacing changes)
set -eu

KTFMT="$1"
WORK_DIR="${2:-.}"
cd "$WORK_DIR"

# Create a test Kotlin file with poor formatting (no space before brace)
cat > Test.kt <<'EOF'
fun main(){
println("hello")
}
EOF

# Assertion 1: --version works
"$KTFMT" --version
echo "✅ --version OK"

# Assertion 2: --help works
"$KTFMT" --help
echo "✅ --help OK"

# Assertion 3: --google-style formats Test.kt
"$KTFMT" --google-style Test.kt

# Verify formatting: Google style adds space before brace
if grep -q 'fun main() {' Test.kt; then
    echo "✅ --google-style formatting verified"
else
    echo "❌ ktfmt did not format the Kotlin file"
    exit 1
fi

echo "All ktfmt smoke tests passed"
