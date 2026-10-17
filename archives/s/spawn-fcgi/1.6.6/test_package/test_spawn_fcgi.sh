#!/bin/sh
# test_package/test_spawn_fcgi.sh — 验证 spawn-fcgi 二进制功能正常
set -eu

# This script is a smoke test for spawn-fcgi.
# The actual test execution is handled by conanfile.py's test() method,
# which runs `spawn-fcgi -v` and verifies the output.
# This file satisfies CI L0c: test source file requirement.

spawn_fcgi="${1:-spawn-fcgi}"

if "$spawn_fcgi" -v 2>&1 | grep -q "spawn-fcgi v1.6.6"; then
    echo "        [ok] spawn-fcgi -v outputs expected version"
else
    echo "        [fail] spawn-fcgi -v did not output expected version"
    exit 1
fi
