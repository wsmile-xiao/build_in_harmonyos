#!/bin/sh
# Smoke test for apcupsd — verifies the binary is installed and functional
# R34: test must call the tested package's binary
set -e

APCUPSD="${1:-apcupsd}"
echo "Testing: $APCUPSD --version"
"$APCUPSD" --version
echo "PASS: apcupsd binary functional"
