#!/bin/sh
# Test script for man-db — verify the man binary works
# This script is called by the conan test_package
set -e

MAN_BIN="${1:-man}"
"$MAN_BIN" --version
echo "man-db test passed"
