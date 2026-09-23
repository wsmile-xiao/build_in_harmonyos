#!/usr/bin/env bash
# test_package/test_pipebench.sh — pipebench 消费者功能测试（R34 真实调用被测二进制）。
# 用法：bash test_pipebench.sh <pipebench 二进制绝对路径>
# 3 个用例：-h 横幅校验、-q 管道直通完整性、-Q 静默直通完整性。
set -euo pipefail

BIN="${1:?Usage: test_pipebench.sh <pipebench binary>}"
if [ ! -x "$BIN" ]; then
  echo "[fail] pipebench binary not executable: $BIN"
  exit 1
fi

# 用例 1：-h 打印版本横幅并退出 0。
HELP_OUT="$("$BIN" -h 2>&1)"
echo "$HELP_OUT" | grep -q "Pipebench 0.40"
echo "[ok] case1 -h banner verified"

# 用例 2：-q 模式管道直通数据必须逐字节一致（pipebench 核心功能：坐在管道中间转发数据）。
echo "pipebench passthrough payload 0123456789 ABCDEFG" > input_case2.bin
"$BIN" -q < input_case2.bin > output_case2.bin 2> stderr_case2.log
cmp input_case2.bin output_case2.bin
echo "[ok] case2 -q passthrough byte-identical"

# 用例 3：-Q 静默模式同样保证直通数据一致。
head -c 65536 /dev/urandom > input_case3.bin
"$BIN" -Q < input_case3.bin > output_case3.bin 2> stderr_case3.log
cmp input_case3.bin output_case3.bin
echo "[ok] case3 -Q passthrough byte-identical"

echo "[ok] test passed: 3/3 pipebench consumer cases verified"
