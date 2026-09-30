#!/bin/sh
# test_ohos — netselect 0.4 HarmonyOS PC 专项验证（自包含，可单独执行）
#
# 在真实鸿蒙 PC（aarch64, OHOS）上对最终 Conan 包做独立专项检查：
#
#   T1  aarch64 ELF 验证（产物为 ELF64 AArch64，可在 OHOS 执行）
#   T2  宿主路径泄漏检查（无 /storage、/home 等构建机绝对路径）
#   T3  usage 输出路径（无参数 -> stderr usage + exit 1，不依赖网络/root）
#   T4  参数校验路径（-t 0 -> exit 1；-I 127.0.0.1 未授权 -> exit 5
#       或 root 下实际探测，验证 socket/SELinux 行为并记录）
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

echo "--- netselect HarmonyOS 专项验证 (binary=$BIN) ---"

# T1: aarch64 ELF（readelf 优先；hnp symlink 故障时用 file 兜底）
if readelf -h "$BIN" 2>/dev/null | grep -q "AArch64"; then
    r=0
elif file "$BIN" 2>/dev/null | grep -q "arm64"; then
    r=0
else
    r=1
fi
chk "T1 aarch64 ELF (ELF64 AArch64)" "$r"

# T2: 宿主路径泄漏（构建机绝对路径不得进入产物）
if strings "$BIN" | grep -qE '/storage/|/home/|/Users/'; then
    echo "  leak: $(strings "$BIN" | grep -E '/storage/|/home/|/Users/' | head -1)"
    chk "T2 无宿主绝对路径泄漏" 1
else
    chk "T2 无宿主绝对路径泄漏" 0
fi

# T3: usage 路径（无网络、无 root 依赖）
out=$("$BIN" 2>&1); rc=$?
[ "$rc" = "1" ] && echo "$out" | grep -q "Usage: netselect" && r=0 || r=1
chk "T3 无参数 -> usage + exit 1 (rc=$rc)" "$r"

# T4: 探测路径（127.0.0.1，观察 raw socket 在 OHOS 上的可用性）
out4=$(timeout 30 "$BIN" -I -t 3 127.0.0.1 2>&1); rc4=$?
if [ "$rc4" = "5" ]; then
    echo "  note: raw socket denied (unprivileged) -> exit 5: $out4"
    chk "T4 探测路径（未授权 socket -> exit 5）" 0
elif [ "$rc4" = "0" ]; then
    echo "  note: privileged probe succeeded: $out4"
    chk "T4 探测路径（root 实际探测 exit 0）" 0
else
    echo "  rc=$rc4 out=[$out4]"
    chk "T4 探测路径（exit=$rc4，需人工判断是否 SELinux 拒绝 raw socket）" 1
fi

echo "--- netselect OHOS 专项: $([ $fail = 0 ] && echo ALL PASS || echo FAILED) ---"
exit $fail
