#!/bin/bash
set -euo pipefail
# Test: mp3val binary works and reports correct version
# Run by test_package/conanfile.py test() method
if mp3val -v 2>&1 | grep -q "0.1.8"; then
    echo "PASS: mp3val binary works correctly"
    exit 0
else
    echo "FAIL: mp3val binary does not work"
    exit 1
fi
