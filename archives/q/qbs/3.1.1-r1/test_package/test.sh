#!/usr/bin/env bash
# qbs test: verify binary works with version and help
set -euo pipefail

TARGET="$1"

if [ -z "$TARGET" ]; then
    echo "Usage: $0 <qbs-binary>"
    exit 1
fi

echo "Testing qbs binary: $TARGET"

# Test --version
echo "=== qbs --version ==="
"$TARGET" --version
echo ""

# Test --help
echo "=== qbs --help ==="
"$TARGET" --help
echo ""

echo "All tests passed!"