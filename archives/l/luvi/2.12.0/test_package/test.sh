#!/bin/sh
# 消费者测试（豁免说明见 MANIFEST.yml）：
# luvi 是 luvit 运行时骨架，单独构建（无 luvit 层 init.lua）时入口
# require('init') 不可用，运行 app/--version 均报 module 'init' not found
# （OHOS 受限 + 无 luvit 层，与上游测试豁免同因）。
# 故本测试验证：二进制存在、可执行、LuaJIT VM 正常启动（报 init 缺失
# 属预期，证明运行时机制工作）。
set -eu

LUVI="${1:-}"
if [ -z "$LUVI" ]; then
    echo "FAIL: luvi binary path not provided"
    exit 1
fi

# 断言 1：二进制存在且可执行
if [ ! -f "$LUVI" ]; then
    echo "FAIL: luvi binary missing: $LUVI"
    exit 1
fi
if [ ! -x "$LUVI" ]; then
    echo "FAIL: luvi binary not executable: $LUVI"
    exit 1
fi
echo "PASS: luvi binary exists and is executable"

# 断言 2：可执行（LuaJIT VM 正常启动——无 app 时入口 require('init')
# 报错属预期，证明运行时加载 LuaJIT/luv 模块成功）
OUT=$("$LUVI" --version 2>&1) || true
echo "luvi run output: $(echo "$OUT" | head -1)"
case "$OUT" in
    *"module 'init' not found"*) echo "PASS: luvi runs (LuaJIT VM up, entry requires luvit init)" ;;
    *) echo "FAIL: unexpected output (binary may be broken): $OUT"; exit 1 ;;
esac

echo "luvi test_package: OK"
exit 0
