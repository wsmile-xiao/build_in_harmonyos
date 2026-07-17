#!/bin/bash
# test_package consumer smoke test — u-boot-tools 2026.07-r0
set -euo pipefail

MKIMAGE="${1:-mkimage}"

if ! command -v "$MKIMAGE" &>/dev/null; then
    echo "❌ mkimage not found in PATH"
    exit 1
fi

echo "=== mkimage --version ==="
"$MKIMAGE" --version 2>&1

echo ""
echo "=== mkimage --help (head) ==="
"$MKIMAGE" --help 2>&1 | head -10
echo "..."

echo ""
echo "✅ u-boot-tools smoke test passed"
