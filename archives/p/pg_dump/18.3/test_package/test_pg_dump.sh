#!/bin/sh
# test_pg_dump.sh — Test script for pg_dump package
# Verifies that pg_dump, pg_dumpall, and pg_restore binaries work correctly

set -e

BIN_DIR="${1:-.}"

echo "Testing pg_dump..."
"${BIN_DIR}/pg_dump" --version

echo "Testing pg_dumpall..."
"${BIN_DIR}/pg_dumpall" --version

echo "Testing pg_restore..."
"${BIN_DIR}/pg_restore" --version

echo "All tests passed!"
