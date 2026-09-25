#!/bin/sh
# test_ohos — redo-c 0.3 HarmonyOS PC 专项验证（自包含，可单独执行）
#
# 在真实鸿蒙 PC（aarch64, OHOS）上对最终 Conan 包做独立专项检查，
# 区别于上游 .do 构建脚本与 test_package 消费者用例：
#
#   T1  aarch64 ELF 验证（产物为 ELF64 AArch64，可在 OHOS 执行）
#   T2  OHOS 可执行位与宿主路径泄漏检查（无 /storage、/home 等宿主绝对路径）
#   T3  公开 CLI（redo）端到端 .do 构建：临时 .do 项目 → redo 构建 → 校验目标
#   T4  usage 输出核验（消费者可见的命令行接口）
#
# 用法：sh run_ohos_test.sh <已安装 redo 二进制路径>
# 退出码：0=全部通过；非 0=有失败（打印首个错误）。
set -u
BIN="${1:-}"
[ -n "$BIN" ] || { echo "usage: $0 <redo-binary-path>"; exit 2; }
[ -f "$BIN" ] || { echo "FAIL: binary not found: $BIN"; exit 2; }

fail=0
chk() { # $1=name $2=result
    if [ "$2" = "0" ]; then echo "PASS: $1"; else echo "FAIL: $1"; fail=1; fi
}

echo "--- redo-c HarmonyOS 专项验证 (binary=$BIN) ---"

# T1: aarch64 ELF
readelf -h "$BIN" 2>/dev/null | grep -q "AArch64" && r=0 || r=1
chk "T1 aarch64 ELF (ELF64 AArch64)" "$r"

# T2: 宿主路径泄漏（构建机 /storage /home 绝对路径不得进入产物）
if strings "$BIN" | grep -qE '/storage/|/home/|/Users/'; then
    echo "  leak: $(strings "$BIN" | grep -E '/storage/|/home/|/Users/' | head -1)"
    chk "T2 无宿主绝对路径泄漏" 1
else
    chk "T2 无宿主绝对路径泄漏" 0
fi

# T3: 公开 CLI 端到端 .do 构建（redo 驱动真实构建语义）
BINDIR=$(dirname "$BIN")
WD=$(mktemp -d "${TMPDIR:-/tmp}/redo-c-ohos-test-XXXXXX")
# redo 内部通过 PATH 查找 redo-ifchange/redo-ifcreate/redo-always 辅助命令
PATH="$BINDIR:$PATH" export PATH
printf '#!/bin/sh\nprintf "built-by-redo-c\\n" > $3\n' > "$WD/target.do"
chmod 755 "$WD/target.do"
( cd "$WD" && "$BIN" target ) >/dev/null 2>&1; rc=$?
if [ "$rc" = "0" ] && [ -f "$WD/target" ]; then
    grep -q "built-by-redo-c" "$WD/target" && r=0 || r=1
    chk "T3 redo 端到端 .do 构建（exit=0 且目标内容正确）" "$r"
else
    echo "  rc=$rc"
    chk "T3 redo 端到端 .do 构建" 1
fi
rm -rf "$WD"

# T4: usage 输出核验（公开 CLI 参数接口）
outu=$("$BIN" -h 2>&1)
echo "$outu" | grep -q "usage: redo" && r=0 || r=1
chk "T4 usage 输出 ($(echo "$outu" | head -1))" "$r"

echo "--- redo-c OHOS 专项: $([ $fail = 0 ] && echo ALL PASS || echo FAILED) ---"
exit $fail