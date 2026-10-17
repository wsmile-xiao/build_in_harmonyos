#!/usr/bin/env bash
# test_package/test_clog.sh — consumer tests for clog executable (R34: real binary execution).
set -eu

# HarmonyOS preflight may run without HOME/passwd entry; the patched clog
# falls back to $HOME, so point it somewhere writable when unset.
if [ -z "${HOME:-}" ]; then
  export HOME="${TMPDIR:-/tmp}"
fi

pass=0
fail=0

ok() { pass=$((pass + 1)); echo "PASS: $1"; }
bad() { fail=$((fail + 1)); echo "FAIL: $1"; }

# 1) clog --version prints package string
if clog --version 2>&1 | grep -q "clog 1.3.0"; then
  ok "--version reports clog 1.3.0"
else
  bad "--version output missing clog 1.3.0"
  clog --version 2>&1 || true
fi

# 2) clog --help prints usage
if clog --help 2>&1 | grep -qi "Usage: clog"; then
  ok "--help prints usage"
else
  bad "--help output missing usage"
fi

# 3) Real filter run: rule file highlights a matching line, output keeps content
TMPDIR_TEST="${TMPDIR:-/tmp}/clog-test-$$"
mkdir -p "$TMPDIR_TEST"
trap 'rm -rf "$TMPDIR_TEST"' EXIT
printf 'default rule /severe/ --> bold red line\n' > "$TMPDIR_TEST/clogrc"
if echo "this is a severe message" | clog -f "$TMPDIR_TEST/clogrc" default 2>&1 | grep -q "severe"; then
  ok "filter run keeps matched line content"
else
  bad "filter run lost matched line content"
fi

# 4) Non-matching line passes through unchanged
if echo "plain hello world" | clog -f "$TMPDIR_TEST/clogrc" default 2>&1 | grep -q "plain hello world"; then
  ok "non-matching line passes through"
else
  bad "non-matching line was dropped"
fi

echo "test_clog: ${pass} passed, ${fail} failed"
if [ "$fail" -ne 0 ]; then
  exit 1
fi
