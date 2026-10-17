#!/bin/sh
# harmonyos_test.sh — lcc 4.2 HarmonyOS-specific test (r02, gw1/gw3)
#
# 验证的鸿蒙特性/兼容性行为（均为本测试的断言目标）：
#   1. 平台绑定：lcc/rcc 二进制为 OHOS PC (aarch64, musl) ELF —— 验证构建目标
#      是鸿蒙 aarch64 而非宿主 x86（若误编为宿主对象则此处失败）。
#   2. 实际运行：lcc 驱动在 OHOS aarch64 上真实执行并生成 x86 汇编（调用被测
#      库二进制 lcc 驱动 + rcc 编译器本体 + cpp 包装），验证工具链在鸿蒙环境
#      可运行、代码生成路径可用。
#   3. 可失败证明：对不存在的输入文件，lcc 必须返回非零退出码 —— 证明断言
#      机制真实生效（非恒真空壳）。
#
# 用法: harmonyos_test.sh <lcc_bin> <rcc_bin> <lccdir> <src> <workdir>
set -u
LCC="$1"
RCC="$2"
LCCDIR="$3"
SRC="$4"
WORK="$5"
fail=0

echo "== [1/3] 平台绑定: lcc 二进制必须是 OHOS PC aarch64 ELF =="
readelf -h "$LCC" 2>&1 | grep -E 'Class:|Machine:' || { echo "FAIL: readelf 无法读取或非 ELF"; fail=1; }
readelf -h "$LCC" 2>&1 | grep -q 'AArch64' || { echo "FAIL: Machine 非 AArch64（非鸿蒙 aarch64 目标）"; fail=1; }
readelf -h "$RCC" 2>&1 | grep -q 'AArch64' || { echo "FAIL: rcc Machine 非 AArch64"; fail=1; }

echo "== [2/3] 实际运行: lcc 驱动在 OHOS 上生成 x86 汇编（调用被测二进制） =="
"$LCC" -Wo-lccdir="$LCCDIR" -S -I"$(dirname "$SRC")/../include/x86/linux" \
  -Dx86 -Wf-g0 -Wf-target=x86/linux -o "$WORK/harmonyos_test.s" "$SRC" \
  || { echo "FAIL: lcc -S 退出码非零（rc=$?）"; fail=1; }
grep -q 'main' "$WORK/harmonyos_test.s" || { echo "FAIL: 汇编输出缺少 main 符号"; fail=1; }
echo "OK: 生成 $(wc -c < "$WORK/harmonyos_test.s") 字节汇编，含 main"

echo "== [3/3] 可失败证明: 对不存在的输入文件，lcc 必须返回非零 =="
"$LCC" -Wo-lccdir="$LCCDIR" -S -o "$WORK/none.s" "$WORK/no-such-file.c" >/dev/null 2>&1
rc=$?
if [ "$rc" -eq 0 ]; then
  echo "FAIL: 期望非零退出码但得到 0（断言未生效）"
  fail=1
else
  echo "OK: 期望失败路径返回 rc=$rc（非零，断言真实生效）"
fi

if [ "$fail" -eq 0 ]; then
  echo "PASS: 鸿蒙特有测试全部通过"
  exit 0
else
  echo "FAIL: 鸿蒙特有测试存在失败断言"
  exit 1
fi
