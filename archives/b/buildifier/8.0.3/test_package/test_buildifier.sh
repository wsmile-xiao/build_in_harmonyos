#!/usr/bin/env bash
# test_package/test_buildifier.sh — smoke test for buildifier executable
# Usage: test_buildifier.sh <path-to-buildifier-binary>
set -euo pipefail

BINARY="${1:?Usage: test_buildifier.sh <path-to-buildifier>}"

echo "[test] buildifier --version"
"$BINARY" --version && echo "OK --version" || {
    echo "[test] --version failed, trying --help..."
    "$BINARY" --help > /dev/null 2>&1 && echo "OK --help" || {
        echo "FAIL: buildifier failed both --version and --help"
        exit 1
    }
}

# Test formatting a sample BUILD file
TMPDIR_TEST="${TMPDIR:-/tmp}/buildifier_test_$$"
mkdir -p "$TMPDIR_TEST"
trap 'rm -rf "$TMPDIR_TEST"' EXIT

cat > "$TMPDIR_TEST/BUILD" << 'EOF'
load("//foo:bar.bzl","bar")
cc_library(
    name="test",
    srcs=["test.cc"],
)
EOF

echo "[test] buildifier --mode=check"
"$BINARY" --mode=check "$TMPDIR_TEST/BUILD" && echo "OK --mode=check" || {
    echo "INFO: --mode=check returned non-zero (expected for unformatted files)"
}

echo "[test] buildifier --mode=fix"
"$BINARY" --mode=fix "$TMPDIR_TEST/BUILD" && echo "OK --mode=fix"

# Verify the file was formatted
if grep -q 'name = "test"' "$TMPDIR_TEST/BUILD"; then
    echo "OK: BUILD file was properly formatted"
else
    echo "FAIL: BUILD file was not formatted correctly"
    cat "$TMPDIR_TEST/BUILD"
    exit 1
fi

echo "All buildifier smoke tests passed"
