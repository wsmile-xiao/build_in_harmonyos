#!/bin/sh
# test_allelecount.sh — 真正运行 alleleCounter 二进制并断言其行为
# (L1d 要求 test() 不是 echo/print/true 假运行: 测试逻辑放在脚本里,
#  conanfile.py 的 test() 仅 self.run("sh test_allelecount.sh")。)
# alleleCounter 二进制由 conanrun 环境注入 PATH(包 bin 目录)。
set -e

if ! command -v alleleCounter >/dev/null 2>&1; then
    echo "FAIL: alleleCounter not found in PATH (conanrun env should inject package bin)"
    exit 1
fi

# alleleCounter 无参数运行时打印 Usage 并退出非零;捕获输出验证二进制
# 真正加载(而非缺失依赖崩溃)。grep 到 Usage 即 PASS。
OUT="$(alleleCounter 2>&1 || true)"
if echo "$OUT" | grep -qi "usage"; then
    echo "PASS: alleleCounter runs and prints usage"
    exit 0
fi
echo "FAIL: alleleCounter did not print expected usage; output was:"
echo "$OUT"
exit 1
