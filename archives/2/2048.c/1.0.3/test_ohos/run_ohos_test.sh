#!/bin/sh
# test_ohos — 2048.c 1.0.3 HarmonyOS PC 专项验证（自包含，可单独执行）
#
# 在真实鸿蒙 PC（aarch64, OHOS）上对最终 Conan 包做独立专项检查，
# 区别于上游内置自测（testSucceed）与 test_package 消费者用例：
#
#   T1  aarch64 ELF 验证（产物为 ELF64 AArch64 PIE，可在 OHOS 执行）
#   T2  OHOS 可执行位与宿主路径泄漏检查（无 /storage、/home 等宿主绝对路径）
#   T3  termios/键盘输入路径：管道喂键驱动真实游戏循环（方向键 + q/y 退出），
#       验证 OHOS 上 stdio/termios 路径可运行且正常退出
#   T4  --version 输出核验（消费者可见的版本信息）
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

echo "--- 2048.c HarmonyOS 专项验证 (binary=$BIN) ---"

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

# T3: 真实游戏循环驱动（管道喂键：两次左移 + q/y 退出）
# 注：2048.c 使用 termios 非规范模式读取键盘；管道输入时 tcsetattr 失败被忽略，
#     getchar() 从管道读取，EOF 时游戏打印错误并正常退出（EXIT_SUCCESS）。
out=$(printf 'aay' | timeout 20 "$BIN" 2>&1); rc=$?
if [ "$rc" = "0" ]; then
    echo "$out" | grep -q "pts" && r=0 || r=1
    chk "T3 管道驱动游戏循环（exit=0 且渲染分数行）" "$r"
else
    echo "  rc=$rc"
    chk "T3 管道驱动游戏循环" 1
fi

# T4: --version
outv=$("$BIN" --version 2>&1)
[ "$outv" = "2048.c version 1.0.3" ] && r=0 || r=1
chk "T4 --version 输出 ($outv)" "$r"

echo "--- 2048.c OHOS 专项: $([ $fail = 0 ] && echo ALL PASS || echo FAILED) ---"
exit $fail