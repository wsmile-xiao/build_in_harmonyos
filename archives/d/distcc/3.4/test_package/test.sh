#!/bin/bash
# test_package/test.sh — distcc smoke test
# Runs distcc --version to verify the binary is functional

set -e
distcc --version
echo "distcc smoke test: PASS"
