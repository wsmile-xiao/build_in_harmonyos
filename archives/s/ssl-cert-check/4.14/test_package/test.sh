#!/usr/bin/env bash
# Test script for ssl-cert-check
# Verifies the installed ssl-cert-check script runs and produces expected output
set -euo pipefail

# Run ssl-cert-check -h and verify output contains "Usage"
output=$(ssl-cert-check -h 2>&1)
echo "$output" | head -5
echo "$output" | grep -q "Usage"
echo "TEST PASSED: ssl-cert-check -h produces expected output"
