#!/usr/bin/env bash
# test_package/test.sh — behavior test for the installed clac executable.
# Mirrors upstream test/tests.sh semantics: assert real calculator output.
# Runs in conanrun env (PATH includes the installed bin/).
set -euo pipefail

fail() { echo "FAIL: $1"; exit 1; }

echo "[test] single positive number"
out=$(clac 3) || fail "clac 3 exited non-zero"
[ "$out" = "3" ] || fail "clac 3 -> expected '3', got '$out'"
echo "PASS: clac 3 == 3"

echo "[test] basic arithmetic"
out=$(clac "3 4 +") || fail "clac '3 4 +' exited non-zero"
[ "$out" = "7" ] || fail "clac '3 4 +' -> expected '7', got '$out'"
echo "PASS: clac '3 4 +' == 7"

echo "[test] summation operator"
out=$(clac "1 2 3 4 sum") || fail "clac '1 2 3 4 sum' exited non-zero"
[ "$out" = "10" ] || fail "clac '1 2 3 4 sum' -> expected '10', got '$out'"
echo "PASS: clac '1 2 3 4 sum' == 10"

echo "[test] user-defined words via CLAC_WORDS"
words_file="${TMPDIR:-$(pwd)}/clac_test_words.txt"
printf 'pi 3.141592\ntau "pi 2 *"\n' > "$words_file"
out=$(CLAC_WORDS="$words_file" clac pi) || fail "clac pi exited non-zero"
[ "$out" = "3.141592" ] || fail "clac pi -> expected '3.141592', got '$out'"
out=$(CLAC_WORDS="$words_file" clac tau) || fail "clac tau exited non-zero"
[ "$out" = "6.283184" ] || fail "clac tau -> expected '6.283184', got '$out'"
rm -f "$words_file"
echo "PASS: user words pi/tau"

echo "ALL PASS: clac behavior test (5 assertions)"
