#!/bin/sh
set -eu
# checkbashisms smoke test

if command -v checkbashisms >/dev/null 2>&1; then
    echo "checkbashisms found in PATH"
    checkbashisms --version
    echo "checkbashisms --version: OK"
    checkbashisms --help >/dev/null 2>&1
    echo "checkbashisms --help: OK"
else
    echo "FAIL: checkbashisms not found"
    exit 1
fi