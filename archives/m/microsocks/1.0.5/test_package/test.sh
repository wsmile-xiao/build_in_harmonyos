#!/bin/bash
set -euo pipefail

if command -v microsocks >/dev/null 2>&1; then
    echo "microsocks found in PATH"
    microsocks --help 2>&1 | head -3
    echo "microsocks: OK"
else
    echo "FAIL: microsocks not found"
    exit 1
fi