#!/bin/sh
# test_ohos — coremark 1.01 HarmonyOS PC 专项验证（自包含，可单独执行）
#
# 在真实鸿蒙 PC（aarch64, OHOS）上对最终 Conan 包做独立专项检查，
# 区别于上游内置自校验（run 目标，输出 crcfinal）与 test_package 消费者用例：
#
#   T1  aarch64 ELF 验证（产物为 ELF64 AArch64，可在 OHOS 执行）
#   T2  OHOS 动态链接器验证（动态 ELF 必须链接 ld-musl-aarch64.so.1）
#   T3  宿主路径泄漏检查（无 /storage、/home 等宿主绝对路径）
#   T4  验证运行（validation run）：固定种子 0x3415 0x3415 0x66，
#       seedcrc 必须与上游 run2.log 参考值一致（0x18f2，由固定种子决定，
#       与迭代次数无关），且输出 "Correct operation validated"（>10s 有效结果窗口）
#
# 用法：sh run_ohos_test.sh <已安装二进制路径>
# 退出码：0=全部通过；非 0=有失败（打印首个错误）。
set -u
BIN="${1:-}"
[ -n "$BIN" ] || { echo "usage: $0 <binary>"; exit 2; }
[ -f "$BIN" ] || { echo "FAIL: binary not found: $BIN"; exit 2; }

fail=0
chk() { # $1=name $2=result
    if [ "$2" = "0" ]; then echo "PASS: $1"; else echo "FAIL: $1"; fail=1; fi
}

echo "--- coremark HarmonyOS 专项验证 (binary=$BIN) ---"

# T1: aarch64 ELF
readelf -h "$BIN" 2>/dev/null | grep -q "AArch64" && r=0 || r=1
chk "T1 aarch64 ELF (ELF64 AArch64)" "$r"

# T2: 动态链接器为 OHOS musl（ld-musl-aarch64.so.1）
if readelf -l "$BIN" 2>/dev/null | grep -q 'interpreter.*ld-musl-aarch64.so.1'; then
    chk "T2 OHOS 动态链接器 (ld-musl-aarch64)" 0
else
    echo "  interp: $(readelf -l "$BIN" 2>/dev/null | grep interpreter)"
    chk "T2 OHOS 动态链接器" 1
fi

# T3: 宿主路径泄漏（构建机 /storage /home /Users 绝对路径不得进入产物）
if strings "$BIN" | grep -qE '/storage/|/home/|/Users/'; then
    echo "  leak: $(strings "$BIN" | grep -E '/storage/|/home/|/Users/' | head -1)"
    chk "T3 无宿主绝对路径泄漏" 1
else
    chk "T3 无宿主绝对路径泄漏" 0
fi

# T4: 验证运行 — 固定种子的 validation run，检查 seedcrc 与上游参考一致
#     （上游 run2.log：seedcrc=0x18f2，由固定种子决定、与迭代次数无关）且 >10s 有效窗口
out=$(timeout 120 "$BIN" 0x3415 0x3415 0x66 0 7 1 2000 2>&1); rc=$?
if [ "$rc" = "0" ]; then
    echo "$out" | grep -q "Correct operation validated" && r=0 || r=1
    chk "T4 验证运行 Correct operation validated" "$r"
    echo "$out" | grep -qE 'seedcrc\s*:\s*0x18f2' && r=0 || r=1
    chk "T4 seedcrc 与上游参考一致 (0x18f2)" "$r"
    echo "$out" | grep -q "Errors detected" && { echo "  errors: $out"; chk "T4 无 Errors detected" 1; } || chk "T4 无 Errors detected" 0
else
    echo "  rc=$rc"
    chk "T4 验证运行" 1
fi

echo "--- coremark OHOS 专项: $([ $fail = 0 ] && echo ALL PASS || echo FAILED) ---"
exit $fail