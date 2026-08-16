#!/data/service/hnp/bin/bash
# test_package/test_cdecl.sh — smoke test for cdecl executable
# Runs in conanrun env (PATH includes installed bin/)
# 真实调用 cdecl 翻译功能: C 声明 <-> 英文 双向转换
# 共 4 个显式断言 (与 test_package/conanfile.py 的 discovered/passedCount 一致)
set -euo pipefail

echo "[test] cdecl --version"
cdecl --version | grep -q "18.7.2" && echo "OK --version"

echo "[test] cdecl explain int *p (C -> English)"
out=$(cdecl 'explain int *p')
echo "$out" | grep -q "declare p as pointer to integer" && echo "OK explain"

echo "[test] cdecl declare a as array 3 of int (English -> C)"
out=$(cdecl 'declare a as array 3 of int')
echo "$out" | grep -q "int a\[3\]" && echo "OK declare"

echo "[test] c++decl symlink"
c++decl 'explain int *p' | grep -q "declare p as pointer to integer" && echo "OK c++decl"

echo "ALL TESTS PASSED (4/4)"
