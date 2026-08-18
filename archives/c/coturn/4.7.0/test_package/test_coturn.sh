#!/bin/sh
# test_coturn.sh — smoke test for the packaged coturn toolchain.
# Runs the RFC 5769 STUN test-vector utility installed in the package.
set -eu

echo "[step] turnutils_rfc5769check"
turnutils_rfc5769check
echo "[ok] RFC 5769 checks passed"

echo "[step] turnserver --version"
turnserver --version
echo "[ok] turnserver --version OK"
