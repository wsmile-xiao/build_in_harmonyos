#!/bin/sh
# test_package smoke tests for agetty 2.42.2 (executed by test_package/conanfile.py)
# Upstream: util-linux 2.42.2 has no registered agetty test cases (0/0 N/A).
# These are consumer-level smoke assertions on the installed binary.

set -e

echo "== smoke 1: agetty --version =="
agetty --version 2>&1 | tee /tmp/agetty-version.out
grep -q 'util-linux 2.42.2' /tmp/agetty-version.out

echo "== smoke 2: agetty --help =="
agetty --help >/dev/null 2>&1

echo "agetty smoke tests PASS"
