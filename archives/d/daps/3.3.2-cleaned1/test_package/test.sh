#!/data/service/hnp/bin/bash
# daps 消费者测试：实质执行安装后的 daps 命令并断言返回码
set -euo pipefail

DAPS_BIN="${DAPS_BIN:?DAPS_BIN 环境变量未设置}"
DAPS_CHECK="${DAPS_CHECK:-${DAPS_BIN%-daps}-check-deps}"

fail() {
    echo "FAIL: $*" >&2
    exit 1
}

# 1. daps --version 输出版本号
out="$("$DAPS_BIN" --version)" || fail "daps --version 执行失败"
echo "$out" | grep -q "3.3.2" || fail "daps --version 未输出版本号 3.3.2（输出: $out）"

# 2. daps --help 输出使用帮助
"$DAPS_BIN" --help >/dev/null || fail "daps --help 执行失败"

# 3. daps --commands 列出支持子命令
"$DAPS_BIN" --commands >/dev/null || fail "daps --commands 执行失败"

# 4. daps-check-deps 运行时依赖探测
"$DAPS_CHECK" >/dev/null || fail "daps-check-deps 执行失败"

echo "daps consumer test passed (4 assertions)"