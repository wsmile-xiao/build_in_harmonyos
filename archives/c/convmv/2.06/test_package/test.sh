#!/bin/bash
set -euo pipefail

if command -v convmv >/dev/null 2>&1; then
    echo "convmv found in PATH"
    convmv --help 2>&1 | head -5
    echo "convmv --help: OK"
else
    echo "FAIL: convmv not found"
    exit 1
fi