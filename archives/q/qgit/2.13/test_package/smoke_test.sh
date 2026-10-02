#!/bin/sh
# smoke_test.sh — qgit 2.13 test_package 测试源（L0c 门禁）
#
# 真实调用被测包打包的二进制并断言可观察结果（不是空壳/只打印字符串）：
#   T1: --version 输出 "QGit 2.13" 且 rc=0（QCommandLineParser 在 GUI 事件循环前处理）
#   T2: --help 输出使用说明（含 "QGit" 与 "Usage" 文本）
# 由 test_package/conanfile.py 的 test() 注入 Qt offscreen 运行环境后通过
# self.run 实际执行（L0d）。上游 qgit 无测试套件（无 tests/、无 add_test），
# 此冒烟测试为按 R51 补全的鸿蒙特有测试。
#
# 用法: sh smoke_test.sh <qgit 二进制路径>
# 退出码: 0=全部断言通过; 1=断言失败; 2=用法/参数错误
set -u
BIN="${1:-}"

[ -n "$BIN" ] && [ -f "$BIN" ] || { echo "usage: $0 <qgit-binary>"; exit 2; }

fail=0
chk() { if [ "$2" = "0" ]; then echo "PASS: $1"; else echo "FAIL: $1"; fail=1; fi }

echo "--- qgit 2.13 test_package smoke test (QT_QPA_PLATFORM=offscreen) ---"

# T1: --version 输出准确版本号且退出码为 0
out=$("$BIN" --version 2>&1); rc=$?
echo "$out" | grep -q "QGit 2.13" && [ "$rc" = "0" ] && r=0 || r=1
chk "T1 --version 输出 'QGit 2.13' 且 rc=0 (rc=$rc)" "$r"

# T2: --help 输出程序说明且退出码为 0
out=$("$BIN" --help 2>&1); rc=$?
echo "$out" | grep -q "QGit" && echo "$out" | grep -qi "usage\|options" \
    && [ "$rc" = "0" ] && r=0 || r=1
chk "T2 --help 输出 QGit 帮助文本且 rc=0 (rc=$rc)" "$r"

if [ "$fail" = "0" ]; then echo "--- smoke test: ALL PASS ---"; else echo "--- smoke test: FAILED ---"; fi
exit $fail
