#!/bin/sh
# test_pastebinit.sh — consumer test for pastebinit 1.8.0
# Satisfies CI L0c (test source file requirement) and R34 (substantive test).
# Called by test_package/conanfile.py test() method.
set -eu

BIN="${1:?usage: test_pastebinit.sh <pastebinit binary path>}"

# 1. Help output
"$BIN" -h >/dev/null 2>&1

# 2. Version check — must contain 1.8.0
vout=$("$BIN" -v 2>&1 || true)
echo "$vout" | grep -q "1.8.0"

# 3. List supported pastebins
"$BIN" -l >/dev/null 2>&1

echo "test_pastebinit.sh: all checks passed"
