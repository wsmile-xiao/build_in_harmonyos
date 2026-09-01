#!/bin/sh
# test_package/test.sh — smoke test for spin executable
set -euo pipefail

echo "[test] spin -V"
spin -V && echo "✅ spin -V OK" || {
    echo "❌ spin -V failed"
    exit 1
}
