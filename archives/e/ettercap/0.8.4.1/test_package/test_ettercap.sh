#!/usr/bin/env bash
# test_ettercap.sh — smoke test for ettercap binaries
# R34: substantively exercises the tested package by running its CLI binaries.
# This script is invoked by test_package/conanfile.py test() method.
# Uses pipefail so that a missing/non-executable binary (L1e sabotage) causes
# a real failure instead of being masked by `| head`.

set -euo pipefail

ETTERCAP_BIN="${1:-ettercap}"
ETTERFILTER_BIN="${2:-etterfilter}"
ETTERLOG_BIN="${3:-etterlog}"

# Verify the binaries exist and are executable before running (R34).
# L1e negative test moves bin/ away — this must fail hard.
for b in "$ETTERFILTER_BIN" "$ETTERLOG_BIN" "$ETTERCAP_BIN"; do
    if [ ! -x "$b" ]; then
        echo "FAIL: binary not found or not executable: $b" >&2
        exit 1
    fi
done

echo "=== Testing etterfilter --version ==="
"$ETTERFILTER_BIN" --version 2>&1

echo "=== Testing etterlog --version ==="
"$ETTERLOG_BIN" --version 2>&1

echo "=== Testing ettercap --version ==="
# ettercap emits dissector warnings to stderr but should exit 0.
# Do NOT pipe through head — pipefail + head causes SIGPIPE (141).
"$ETTERCAP_BIN" --version 2>&1

echo "=== All smoke tests passed ==="
exit 0
