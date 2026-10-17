#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for zuo executable
# Runs in conanrun env (PATH includes installed bin/)
set -eu

echo "[test] zuo --help"
zuo --help > /dev/null
echo "PASS: --help OK"

echo "[test] zuo hello.zuo (interpreter + module system)"
zuo hello.zuo | grep -q "Hello, world!"
echo "PASS: hello.zuo OK"

echo "[test] zuo filetest.zuo (fd file I/O + string/arith primitives)"
rm -f out.txt
zuo filetest.zuo
echo "PASS: filetest.zuo OK"

echo "ALL ZUO SMOKE TESTS PASSED"
