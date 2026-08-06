#!/usr/bin/env bash
# test_package/test.sh — smoke test for easyrsa executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

TEST_PKI_DIR="${TMPDIR:-/tmp}/easyrsa-test-pki-$$"
rm -rf "$TEST_PKI_DIR"

echo "[test] easyrsa --version"
easyrsa --version
VERSION_LINE=$(easyrsa --version 2>&1 | grep "^Version:")
echo "$VERSION_LINE" | grep -q "3.2.6" || { echo "[fail] Version mismatch"; exit 1; }
echo "[ok] --version passed"

echo "[test] easyrsa init-pki"
EASYRSA_PKI="$TEST_PKI_DIR" easyrsa --batch init-pki
[ -d "$TEST_PKI_DIR/private" ] || { echo "[fail] PKI private dir missing"; exit 1; }
[ -d "$TEST_PKI_DIR/issued" ] || { echo "[fail] PKI issued dir missing"; exit 1; }
echo "[ok] init-pki passed"

echo "[test] easyrsa build-ca nopass"
EASYRSA_PKI="$TEST_PKI_DIR" easyrsa --batch build-ca nopass
[ -f "$TEST_PKI_DIR/ca.crt" ] || { echo "[fail] CA certificate missing"; exit 1; }
[ -f "$TEST_PKI_DIR/private/ca.key" ] || { echo "[fail] CA key missing"; exit 1; }
echo "[ok] build-ca passed"

rm -rf "$TEST_PKI_DIR"
echo "All tests passed."
