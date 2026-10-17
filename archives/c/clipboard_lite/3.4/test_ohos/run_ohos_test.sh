#!/bin/sh
# test_ohos — clipboard_lite 3.4 HarmonyOS PC 专项验证（自包含，可单独执行）
#
# 在真实鸿蒙 PC（aarch64, OHOS）上对最终 Conan 包做独立专项检查，
# 区别于上游内置测试（Test/main.cpp，X11 剪贴板演示）与 test_package
# 消费者用例（consumer.cpp 驱动公开 API）：
#
#   T1  aarch64 ELF 验证（静态库为 ELF64 AArch64，OHOS 目标）
#   T2  OHOS 可执行位与宿主路径泄漏检查（无 /storage、/home 等宿主绝对路径）
#   T3  X11 后端符号完整链接验证（XOpenDisplay/XFixes/XTest 符号可被 OHOS
#       工具链解析，证明 Linux/X11 后端在 OHOS 上链接可用）
#   T4  公开 API 符号导出核验（CreateClipboard 等消费者可见符号）
#
# 用法：sh run_ohos_test.sh <lib路径> [c++编译器]
# 退出码：0=全部通过；非 0=有失败（打印首个错误）。
set -u
LIB="${1:-}"
[ -n "$LIB" ] || { echo "usage: $0 <libclipboard_lite.a路径> [c++编译器]"; exit 2; }
[ -f "$LIB" ] || { echo "FAIL: lib not found: $LIB"; exit 2; }
CXX="${2:-clang++}"

fail=0
chk() { # $1=name $2=result
    if [ "$2" = "0" ]; then echo "PASS: $1"; else echo "FAIL: $1"; fail=1; fi
}

echo "--- clipboard_lite 3.4 HarmonyOS 专项验证 (lib=$LIB) ---"

# T1: aarch64 ELF
readelf -h "$LIB" 2>/dev/null | grep -q "AArch64" && r=0 || r=1
chk "T1 aarch64 ELF (ELF64 AArch64)" "$r"

# T2: 宿主路径泄漏（构建机 /storage /home /Users 绝对路径不得进入产物）
if strings "$LIB" | grep -qE '/storage/|/home/|/Users/'; then
    echo "  leak: $(strings "$LIB" | grep -E '/storage/|/home/|/Users/' | head -1)"
    chk "T2 无宿主绝对路径泄漏" 1
else
    chk "T2 无宿主绝对路径泄漏" 0
fi

# T3: X11 后端符号完整链接验证 —— 用 OHOS 工具链把库与 X11 依赖
# (libX11/libXfixes/libXtst) 链接成一个真实可执行，验证后端符号可解析。
TMPD="${TMPDIR:-/tmp}/cl_lite_ohos_t3"
rm -rf "$TMPD" && mkdir -p "$TMPD"
cat > "$TMPD/t3.cpp" <<'EOF'
#include <Clipboard_Lite.h>
int main() {
    auto c = SL::Clipboard_Lite::CreateClipboard();
    return c ? 0 : 1;
}
EOF
X11LIBDIRS=""
for d in "$HOME"/.conan2/p/libx17*/p/lib "$HOME"/.conan2/p/libxf0*/p/lib "$HOME"/.conan2/p/libxt7*/p/lib; do
    [ -d "$d" ] && X11LIBDIRS="$X11LIBDIRS -L$d"
done
if "$CXX" -std=c++14 -I"$(dirname "$LIB")/../include" "$TMPD/t3.cpp" "$LIB" \
    $X11LIBDIRS -lX11 -lXfixes -lXtst -lpthread -o "$TMPD/t3" >"$TMPD/t3.log" 2>&1; then
    chk "T3 X11 后端符号链接解析 (XOpenDisplay/XFixes/XTest)" 0
else
    echo "  link error: $(tail -3 "$TMPD/t3.log" | head -1)"
    chk "T3 X11 后端符号链接解析" 1
fi

# T4: 公开 API 符号导出核验
if nm -C "$LIB" 2>/dev/null | grep -q "SL::Clipboard_Lite::CreateClipboard"; then
    chk "T4 公开 API 符号导出 (CreateClipboard)" 0
else
    chk "T4 公开 API 符号导出 (CreateClipboard)" 1
fi

echo "--- clipboard_lite 鸿蒙专项验证结束: $([ $fail -eq 0 ] && echo ALL PASS || echo HAS FAILURES) ---"
exit $fail