#!/usr/bin/env bash
# test.sh — smoke test for avro-tools
# Runs avro-tools and verifies output contains "Version 1.12.1"

set -e

AVRO_TOOLS="${1:-avro-tools}"
JAVA_HOME="${JAVA_HOME:-/storage/Users/currentUser/usr/local/bishengjdk17}"
export JAVA_HOME
export PATH="$JAVA_HOME/bin:$PATH"

echo "=== Running avro-tools smoke test ==="
output=$("$AVRO_TOOLS" 2>&1 | head -5) || true

if echo "$output" | grep -q "Version 1.12.1"; then
    echo "PASS: avro-tools output contains 'Version 1.12.1'"
    echo "$output"
    exit 0
else
    echo "FAIL: avro-tools output does not contain 'Version 1.12.1'"
    echo "$output"
    exit 1
fi
