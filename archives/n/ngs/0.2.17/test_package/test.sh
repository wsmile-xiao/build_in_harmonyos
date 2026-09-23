#!/data/service/hnp/bin/bash
# test_package/test.sh — Conan L1 冒烟：真实执行被测包安装的 ngs 二进制
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"

# A1: 二进制存在且可执行，版本自证
# ngs 的 stdin 是数据而非程序；表达式求值用 -e（-p 是 JSON 输出选项）
v="$(ngs -e 'echo(VERSION)')"
[ "$v" = "0.2.17" ] || { echo "FAIL: ngs -e 'echo(VERSION)' => '$v'"; exit 1; }
echo "PASS version=$v"

# A2: NGS_PATH 指向包内标准库且已被本次调用加载
[ -n "${NGS_PATH:-}" ] || { echo "FAIL: NGS_PATH not exported by the package"; exit 1; }
[ -f "$NGS_PATH/stdlib.ngs" ] || { echo "FAIL: $NGS_PATH/stdlib.ngs missing"; exit 1; }
echo "PASS NGS_PATH=$NGS_PATH"

# A3: 解释器求值 + 字符串插值
# ngs 的 + 没有 (Str, Int) 重载，字符串拼接一律走 ${...} 插值；
# 函数调用形式与上游 doc/ngslang.1.md 及 lib/lang-tests.ngs 一致。
out="$(ngs -e 'echo("hi ${1+2}")')"
[ "$out" = "hi 3" ] || { echo "FAIL: interp eval => '$out'"; exit 1; }
echo "PASS interp-eval"

# A4..: 依赖链功能断言（json-c / pcre / bdw-gc / libffi）
ngs "$here/ngs_smoke.ngs"

echo "ALL TESTS PASSED"
