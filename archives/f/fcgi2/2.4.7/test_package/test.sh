#!/data/service/hnp/bin/bash
# test_package/test.sh — compiles a consumer program against the installed
# libfcgi and runs it in CGI fallback mode (R34: genuinely uses the API).
# Compile output goes to a temp dir so no artifacts land in the source tree.
set -euo pipefail

echo "[test] consumer compile with -I$FCGI_INC -L$FCGI_LIB"
CXX_BIN=clang
command -v clang >/dev/null 2>&1 || CXX_BIN=cc
OUT="${TMPDIR:-$HOME/tmp}/fcgi2-test-$$"
mkdir -p "$OUT"
trap 'rm -rf "$OUT"' EXIT
"$CXX_BIN" -I"$FCGI_INC" test.c -o "$OUT/fcgi_test" -L"$FCGI_LIB" -lfcgi
echo "OK: consumer program links against libfcgi"

echo "[test] run CGI-mode FCGI_Accept loop"
MSG=$(cd "$OUT" && ./fcgi_test </dev/null 2>&1)
echo "$MSG"
echo "$MSG" | grep -q "fcgi-ok"
echo "OK: FCGI_Accept served one CGI request"

echo "ALL CONSUMER TESTS PASSED"
