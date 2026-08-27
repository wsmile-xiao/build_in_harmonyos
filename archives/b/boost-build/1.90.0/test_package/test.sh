#!/bin/sh
# test.sh — boost-build test_package smoke test
# Verifies b2 binary from the conan package is installed and functional
set -e

B2="${B2_PATH:-b2}"
"$B2" --version
