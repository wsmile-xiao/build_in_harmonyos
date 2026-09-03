#!/usr/bin/env bash
# no-more-secrets 1.0.1 — consumer smoke test (same checks as conanfile.py test()).
# Usage: bash test.sh <absolute-path-to-package-bin-dir>
set -euo pipefail

BIN_DIR="${1:-}"
if [ -z "$BIN_DIR" ]; then
    echo "usage: bash test.sh <package bin dir>" >&2
    exit 2
fi

NMS="$BIN_DIR/nms"
SNEAKERS="$BIN_DIR/sneakers"

echo "--- nms -v ---"
"$NMS" -v
"$NMS" -v | grep -q "nms version 1.0.1"
echo "check passed: nms reports version 1.0.1"

echo "--- sneakers presence ---"
test -x "$SNEAKERS"
echo "check passed: sneakers is present and executable"

echo "no-more-secrets smoke test passed"
