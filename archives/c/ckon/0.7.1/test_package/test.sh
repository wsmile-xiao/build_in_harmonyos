#!/usr/bin/env bash
# test_package/test.sh — behavior test for the installed ckon executable.
# ckon is an automatic build tool for ROOT; --version and --help exercise
# the real option parsing (boost::program_options) and print to stdout.
set -euo pipefail

fail() { echo "FAIL: $1"; exit 1; }

echo "[test] ckon --version"
out=$(ckon --version) || fail "ckon --version exited non-zero"
echo "version output: $out"
case "$out" in
  0.7*) : ;;
  *) fail "ckon --version -> unexpected version string '$out'" ;;
esac
echo "PASS: ckon --version reports $out"

echo "[test] ckon --help"
out=$(ckon --help) || fail "ckon --help exited non-zero"
case "$out" in
  *"automatic build tool"*) : ;;
  *) fail "ckon --help -> missing tool description" ;;
esac
echo "PASS: ckon --help prints usage"

echo "ALL PASS: ckon behavior test (2 assertions)"
