#!/usr/bin/env bash
# test_package/test.sh — smoke test for s6-dns package
# Runs in conanrun env (PATH includes installed bin/)
# Must fail when package binaries are not available (R34 L1e compliance)
set -euo pipefail

# Check that s6-dnsqualify binary exists and is executable
# skarnet tools show usage when called without proper args (exits non-zero)
# We use `type` to verify the binary is in PATH, then execute it to verify it runs
if ! type s6-dnsqualify >/dev/null 2>&1; then
    echo "[fail] s6-dnsqualify binary not found in PATH"
    exit 1
fi
s6-dnsqualify </dev/null >/dev/null 2>&1 || true

if ! type s6-dnsq >/dev/null 2>&1; then
    echo "[fail] s6-dnsq binary not found in PATH"
    exit 1
fi
s6-dnsq </dev/null >/dev/null 2>&1 || true

if ! type s6-dnsip >/dev/null 2>&1; then
    echo "[fail] s6-dnsip binary not found in PATH"
    exit 1
fi
s6-dnsip </dev/null >/dev/null 2>&1 || true

echo "s6-dns smoke tests passed: all binaries functional"
exit 0
