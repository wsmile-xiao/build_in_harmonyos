#!/usr/bin/env bash
# test_package/test_runner.sh — PHP smoke test wrapper
# This script satisfies CI L0c (test source file requirement).
# The actual test execution is done via conanfile.py test() method.
set -euo pipefail

PHP="${PHP:-php}"

echo "[test] PHP version"
"$PHP" --version

echo "[test] Arithmetic (1+1)"
"$PHP" -r 'var_dump(1+1);'

echo "[test] String operations (strtoupper)"
"$PHP" -r 'var_dump(strtoupper("hello"));'

echo "[test] JSON encoding"
"$PHP" -r 'var_dump(json_encode(["a"=>1,"b"=>2]));'

echo "[test] Regex matching"
"$PHP" -r 'var_dump(preg_match("/\d+/", "abc123"));'

echo "[test] Script execution"
"$PHP" "$(dirname "$0")/test_script.php"

echo "[test] PHP smoke test: PASS"
