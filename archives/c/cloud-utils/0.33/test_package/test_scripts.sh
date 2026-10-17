#!/bin/sh
# test_package/test_scripts.sh — Functional test for cloud-utils scripts
# Verifies that installed scripts are executable and respond to --help
# Called by test_package/conanfile.py test() method

set -eu

fail=0

# Test growpart (sh script) — partition resizing utility
if growpart --help >/dev/null 2>&1; then
    echo "[ok] growpart --help responds"
else
    echo "[fail] growpart --help failed"
    fail=1
fi

# Test write-mime-multipart (python3 script) — MIME multipart writer
if write-mime-multipart --help >/dev/null 2>&1; then
    echo "[ok] write-mime-multipart --help responds"
else
    echo "[fail] write-mime-multipart --help failed"
    fail=1
fi

# Test cloud-localds (bash script) — cloud-init local data source creator
if cloud-localds --help >/dev/null 2>&1; then
    echo "[ok] cloud-localds --help responds"
else
    echo "[fail] cloud-localds --help failed"
    fail=1
fi

# Note: ec2metadata is not tested because it requires network access
# to EC2 metadata service, which is not available in CI environment.

exit $fail
