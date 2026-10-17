#!/bin/sh
# test_package/test.sh — smoke test for k3d 5.9.0
# $1 = absolute path to the installed k3d binary
# Runs in conanrun env; cwd is a writable TMPDIR (HMBS injects SHELL=/bin/sh).
set -eu

K3D="$1"

echo "[test] k3d version"
OUT="$("$K3D" version 2>&1)"
echo "$OUT"
echo "$OUT" | grep -q "v5.9.0" && echo "[test] OK: version reports v5.9.0" || {
    echo "[test] FAIL: k3d version did not report v5.9.0" >&2
    exit 1
}

echo "[test] k3d --help"
"$K3D" --help > /dev/null 2>&1 && echo "[test] OK: --help works" || {
    echo "[test] FAIL: k3d --help failed" >&2
    exit 1
}

echo "[test] k3d smoke test passed (2/2)"
