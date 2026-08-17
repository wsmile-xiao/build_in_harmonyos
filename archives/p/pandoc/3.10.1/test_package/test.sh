#!/data/service/hnp/bin/bash
# test_package/test.sh — pandoc 3.10.1 smoke test
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[test] pandoc --version"
pandoc --version
pandoc --version | grep -q "3.10.1" && echo "✅ version 3.10.1 OK" || {
    echo "❌ pandoc --version 未输出 3.10.1"
    exit 1
}

echo "[test] markdown -> html 实际转换"
out=$(printf '# Hello\n\nworld\n' | pandoc -f markdown -t html)
echo "$out"
echo "$out" | grep -q "<h1" && echo "✅ markdown→html 转换 OK" || {
    echo "❌ markdown→html 转换失败"
    exit 1
}

echo "[test] --list-output-formats 可用"
pandoc --list-output-formats | grep -q "html" && echo "✅ 输出格式列表 OK" || {
    echo "❌ pandoc --list-output-formats 失败"
    exit 1
}

echo "[test] 上游命令测试精选用例（command_tests/，51 个，字节级比对）"
# 由 AI 从上游 test/command/ 精选移植的可执行用例套件（见 command_tests/README.md）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bash "${SCRIPT_DIR}/command_tests/run_command_tests.sh" || {
    echo "❌ command_tests 命令测试套件未全部通过"
    exit 1
}

echo "✅ pandoc smoke test 全部通过"
