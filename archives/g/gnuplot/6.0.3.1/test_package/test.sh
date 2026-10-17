#!/bin/bash
# test.sh — gnuplot L1 smoke + functional test
# Runs gnuplot binary to verify version and PNG image output (requires gd support)
set -e

# 1. Smoke test: verify the binary works
gnuplot --version

# 2. Functional test: generate a PNG image (requires gd support)
gnuplot -e "set terminal png; set output 'test_output.png'; plot sin(x)"

# 3. Verify the PNG file was created and is non-empty
if [ ! -f test_output.png ]; then
    echo "ERROR: PNG output file was not created"
    exit 1
fi
if [ ! -s test_output.png ]; then
    echo "ERROR: PNG output file is empty"
    exit 1
fi

echo "All tests passed."
