#!/usr/bin/env bash
# test_package/test.sh — xclicker 消费者验证 + 鸿蒙特有平台检查
#
# 断言：
#   A. 产物存在且为 ELF（od 读魔数，无外部依赖）
#   B. 鸿蒙特有：ELF machine = AArch64，动态链接器为 OHOS musl
#      （/lib/ld-musl-aarch64.so.1），且含 .codesign 签名段
#   C. 鸿蒙特有：NEEDED 链接到 OHOS 适配后的 GTK/X11 栈
#      （libgtk-3.so.0 / libX11.so.6 / libXi.so.6 / libXtst.so.6）
#   D. 真实执行：`xclicker --help` 退出 0 并输出用法 —— 该命令在 main()
#      之前加载全部 NEEDED 动态库，等价于验证 OHOS 上运行期依赖闭包完整
#      （沙箱无 X display，无法进入 GTK 主循环，故不做 UI 交互）
set -uo pipefail

echo "--- xclicker consumer verification (OHOS) ---"

pass=0
fail=0
ok()  { echo "PASS: $1"; pass=$((pass + 1)); }
bad() { echo "FAIL: $1"; fail=$((fail + 1)); }

BIN="$(command -v xclicker || true)"
if [ -z "$BIN" ]; then
    echo "FAIL: xclicker 不在 PATH 上（conanrun 未注入包 bin/）"
    exit 1
fi
echo "binary: $BIN"

# ── A. ELF 魔数 ────────────────────────────────────────────────────
magic="$(od -An -tx1 -N4 "$BIN" | tr -d ' \n')"
if [ "$magic" = "7f454c46" ]; then
    ok "产物为 ELF（magic=$magic）"
else
    bad "产物不是 ELF（magic=$magic）"
fi

# ── B/C. 鸿蒙特有：平台与依赖栈 ────────────────────────────────────
READELF="$(command -v llvm-readelf || command -v readelf || true)"
if [ -n "$READELF" ]; then
    hdr="$("$READELF" -h "$BIN" 2>/dev/null || true)"
    if echo "$hdr" | grep -q "AArch64"; then
        ok "ELF machine = AArch64（OHOS PC 目标架构）"
    else
        bad "ELF machine 非 AArch64：$(echo "$hdr" | grep -i machine | head -1)"
    fi

    interp="$("$READELF" -l "$BIN" 2>/dev/null | grep -i 'program interpreter' | head -1)"
    if echo "$interp" | grep -q "ld-musl-aarch64"; then
        ok "OHOS musl 动态链接器（$(echo "$interp" | sed 's/.*interpreter: //; s/\].*//')）"
    else
        bad "动态链接器非 OHOS musl：$interp"
    fi

    if "$READELF" -S "$BIN" 2>/dev/null | grep -q "\.codesign"; then
        ok "含 .codesign 签名段（OHOS 可执行前提）"
    else
        bad "缺 .codesign 签名段（OHOS 下不可执行）"
    fi

    needed="$("$READELF" -d "$BIN" 2>/dev/null | grep -i NEEDED || true)"
    for lib in libgtk-3.so.0 libX11.so.6 libXi.so.6 libXtst.so.6; do
        if echo "$needed" | grep -q "$lib"; then
            ok "NEEDED $lib（OHOS 适配栈）"
        else
            bad "NEEDED 缺 $lib"
        fi
    done
else
    echo "SKIP: 无 readelf/llvm-readelf，跳过 ELF 平台属性检查"
fi

# ── D. 真实执行（加载全部 NEEDED 库 + GOptionContext 解析）──────────
out="$(timeout 30 "$BIN" --help 2>&1)"
rc=$?
if [ "$rc" = 0 ] && echo "$out" | grep -q "Usage:" && echo "$out" | grep -q -- "--display"; then
    ok "执行 'xclicker --help' 成功（exit 0，输出用法；NEEDED 动态库全部加载成功）"
else
    bad "执行 'xclicker --help' 失败（exit=$rc）：$(echo "$out" | head -3)"
fi

echo "test xclicker 1.5.1: ${pass} passed, ${fail} failed"
[ "$fail" = 0 ] || exit 1
exit 0
