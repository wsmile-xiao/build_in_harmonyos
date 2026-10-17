#!/bin/sh
# test_ohos — libmcfp 2.1.1 HarmonyOS PC 专项验证（自包含，可单独执行）
#
# 在真实鸿蒙 PC（aarch64, OHOS）上对最终 Conan 包做独立专项检查，
# 区别于上游 Catch2 套件（37 用例，conan build() 内已跑）与 test_package
# 消费者用例（test.cpp，-n 7 --text hello -i a -i b）：
#
#   T1  libmcfp.a 归档成员为 ELF64 AArch64（readelf -h）
#   T2  无宿主绝对路径泄漏（/storage、/home、/Users 不进产物）
#   T3  fast_float 浮点路径：真机编译并运行 ohos_ff_test.cpp，
#       -d 3.14159 -f 2.5 解析并断言数值（OHOS 无浮点 std::from_chars，
#       必须走 USE_FAST_FLOAT 适配路径），可执行文件为 ELF64 AArch64
#   T4  ff_charconv 符号存在（charconv-fast_float.cpp 已编入 libmcfp.a）
#
# 用法：sh run_ohos_test.sh <已安装包目录> [CXX] [TMPDIR]
#   包目录需含 include/mcfp/mcfp.hpp 与 lib/libmcfp.a
# 退出码：0=全部通过；非 0=有失败（打印首个错误）。
set -u
PKG="${1:-}"
CXX="${2:-/data/service/hnp/bin/clang++}"
# 默认工作目录用 $HOME 相对路径（可移植，CI 亦设置 HOME），不硬编码执行端绝对路径
WORK="${3:-${TMPDIR:-$HOME/tmp}/libmcfp-ohos-test}"
[ -n "$PKG" ] || { echo "usage: $0 <package-dir> [CXX] [TMPDIR]"; exit 2; }
[ -f "$PKG/include/mcfp/mcfp.hpp" ] || { echo "FAIL: header not found: $PKG/include/mcfp/mcfp.hpp"; exit 2; }
[ -f "$PKG/lib/libmcfp.a" ] || { echo "FAIL: library not found: $PKG/lib/libmcfp.a"; exit 2; }

# 脚本自身绝对目录（在任何 cd 之前解析，供后续编译源码引用）
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

fail=0
chk() { # $1=name $2=result
    if [ "$2" = "0" ]; then echo "PASS: $1"; else echo "FAIL: $1"; fail=1; fi
}

echo "--- libmcfp 2.1.1 HarmonyOS 专项验证 (pkg=$PKG) ---"

# T1: 归档成员 aarch64
OBJ="$WORK/_t1_member.o"
rm -rf "$WORK"; mkdir -p "$WORK"
cd "$WORK" || exit 2
ar x "$PKG/lib/libmcfp.a" 2>/dev/null
if ls *.o >/dev/null 2>&1; then
    readelf -h "$(ls *.o | head -1)" 2>/dev/null | grep -q "AArch64" && r=0 || r=1
else
    r=1
fi
chk "T1 libmcfp.a members ELF64 AArch64" "$r"

# T2: 宿主路径泄漏
if strings "$PKG/lib/libmcfp.a" | grep -qE '/storage/|/home/|/Users/'; then
    echo "  leak: $(strings "$PKG/lib/libmcfp.a" | grep -E '/storage/|/home/|/Users/' | head -1)"
    chk "T2 无宿主绝对路径泄漏" 1
else
    chk "T2 无宿主绝对路径泄漏" 0
fi

# T3: fast_float 路径真机编译 + 运行
SRC="$SCRIPT_DIR/ohos_ff_test.cpp"
# OHOS clang 15 只认识 C++23 草案名 c++2b（拒绝 -std=c++23 字面量）；
# 与 conan 构建（CMake cxx_std_23 → -std=c++2b）保持一致，并显式用 libc++。
"$CXX" -std=c++2b -stdlib=libc++ "$SRC" -I"$PKG/include" "$PKG/lib/libmcfp.a" -o "$WORK/ohos_ff_test" 2>"$WORK/compile.log" && r=0 || r=1
chk "T3c 编译 ohos_ff_test (fast_float 路径)" "$r"
if [ "$r" = "0" ]; then
    readelf -h "$WORK/ohos_ff_test" 2>/dev/null | grep -q "AArch64" && r=0 || r=1
    chk "T3e 可执行文件 ELF64 AArch64" "$r"
    ./ohos_ff_test >"$WORK/run.log" 2>&1 && r=0 || r=1
    chk "T3r 真机运行（-d 3.14159 -f 2.5）" "$r"
    grep -q "OHOS mcfp fast_float test OK" "$WORK/run.log" || { echo "  unexpected output: $(cat "$WORK/run.log")"; fail=1; }
else
    cat "$WORK/compile.log" | head -5
fi

# T4: ff_charconv 符号（charconv-fast_float.cpp 编入库）
if strings "$PKG/lib/libmcfp.a" | grep -q "ff_charconv"; then
    chk "T4 ff_charconv 符号存在 (fast_float 适配已编译)" 0
else
    chk "T4 ff_charconv 符号存在 (fast_float 适配已编译)" 1
fi

[ "$fail" = "0" ] && echo "ALL OHOS SPECIAL TESTS PASSED" || echo "OHOS SPECIAL TESTS FAILED"
exit "$fail"