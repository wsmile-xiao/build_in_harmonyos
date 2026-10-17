#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for cc65 compiler suite (R34).
# Runs in conanrun env (PATH includes installed bin/).
set -euo pipefail

echo "[test] cc65 --version"
cc65 --version | head -1

echo "[test] ca65 --version"
ca65 --version | head -1

echo "[test] cl65 --version"
cl65 --version | head -1

echo "[test] cc65 test.c (compile C to 6502 assembly, cc65 无 -c 选项)"
cc65 test.c

echo "[test] verify assembly output test.s exists"
test -f test.s
rm -f test.s

echo "PASS: cc65 compiler suite functional"
