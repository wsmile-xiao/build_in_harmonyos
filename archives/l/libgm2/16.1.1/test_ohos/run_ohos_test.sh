#!/bin/sh
# test_ohos — libgm2 16.1.1 HarmonyOS PC 专项验证（自包含，可单独执行）
#
# 在真实鸿蒙 PC（aarch64, OHOS）上对最终 Conan 包做独立专项检查，
# 区别于上游测试（gm2 testsuite 冒烟）与 test_consumer 消费者用例：
#
#   OHOS_01  aarch64 ELF 验证（打包运行时库为 ELF64 AArch64，可在 OHOS 加载执行）
#   OHOS_02  OHOS 可执行位与宿主路径泄漏检查（无 /storage、/home 等宿主绝对路径）
#   OHOS_03  真实运行：编译消费者程序链接打包库，执行并核验可观察输出
#   OHOS_04  打包运行时库符号完整性（m2pim_Builtins_strlen 等 C 可调用导出存在）
#
# 用法：sh run_ohos_test.sh <已安装共享库目录> [编译器，默认 clang]
# 退出码：0=全部通过；非 0=有失败（打印首个错误）。
set -u
LIBDIR="${1:-}"
CC="${2:-clang}"
[ -n "$LIBDIR" ] || { echo "usage: $0 <libdir> [compiler]"; exit 2; }
[ -d "$LIBDIR" ] || { echo "FAIL: libdir not found: $LIBDIR"; exit 2; }

READELF=$(command -v llvm-readelf || command -v readelf || echo "")
STRINGS=$(command -v llvm-strings || command -v strings || echo "")

fail=0
chk() { # $1=name $2=result
    if [ "$2" = "0" ]; then echo "PASS: $1"; else echo "FAIL: $1"; fail=1; fi
}

echo "--- libgm2 16.1.1 HarmonyOS 专项验证 (libdir=$LIBDIR) ---"

# 打包的共享库（五项运行时 + 合并 C++ 运行时 stub）
LIBS="libm2cor.so libm2iso.so libm2log.so libm2min.so libm2pim.so"
MISSING=""
for lib in $LIBS; do
    [ -f "$LIBDIR/$lib" ] || MISSING="$MISSING $lib"
done
if [ -n "$MISSING" ]; then
    echo "  missing:$MISSING"
    chk "OHOS_00 打包共享库齐全（5 个运行时 .so）" 1
else
    chk "OHOS_00 打包共享库齐全（5 个运行时 .so）" 0
fi

# OHOS_01: aarch64 ELF（ELF64 AArch64 e_machine=183）
if [ -n "$READELF" ]; then
    bad=0
    for lib in $LIBS; do
        [ -f "$LIBDIR/$lib" ] || continue
        "$READELF" -h "$LIBDIR/$lib" 2>/dev/null | grep -q "AArch64" || { echo "  not aarch64: $lib"; bad=1; }
    done
    chk "OHOS_01 aarch64 ELF（全部 .so 为 ELF64 AArch64）" "$bad"
else
    echo "  readelf unavailable, skipped"
    chk "OHOS_01 aarch64 ELF" 1
fi

# OHOS_02: 宿主路径泄漏（构建机 /storage /home /Users 绝对路径不得进入产物）
if [ -n "$STRINGS" ]; then
    leak=$("$STRINGS" "$LIBDIR"/*.so 2>/dev/null | grep -E '/storage/|/home/|/Users/' | head -1)
    if [ -n "$leak" ]; then
        echo "  leak: $leak"
        chk "OHOS_02 无宿主绝对路径泄漏" 1
    else
        chk "OHOS_02 无宿主绝对路径泄漏" 0
    fi
else
    chk "OHOS_02 无宿主绝对路径泄漏" 1
fi

# OHOS_03: 真实运行——编译消费者程序链接打包库，执行并核验输出
HERE=$(dirname "$0")
SRC="$HERE/../test_consumer/consumer_use_case.c"
WORK=$(mktemp -d "${TMPDIR:-/tmp}/libgm2-ohos.XXXXXX") || exit 2
trap 'rm -rf "$WORK"' EXIT
if [ -f "$SRC" ]; then
    if "$CC" -O2 -Wl,--allow-shlib-undefined \
        -L"$LIBDIR" -lm2iso -lm2pim -lm \
        "$SRC" -o "$WORK/consumer" 2>"$WORK/cc.log"; then
        out=$(LD_LIBRARY_PATH="$LIBDIR" "$WORK/consumer" 2>&1); rc=$?
        if [ "$rc" = "0" ] && echo "$out" | grep -q 'consumer-ok'; then
            chk "OHOS_03 打包库真实运行（编译+链接+执行，rc=0 且输出 consumer-ok）" 0
        else
            echo "  rc=$rc out=$(echo "$out" | head -3)"
            chk "OHOS_03 打包库真实运行" 1
        fi
    else
        echo "  $(head -5 "$WORK/cc.log")"
        chk "OHOS_03 打包库真实运行（编译失败）" 1
    fi
else
    echo "  consumer source not found: $SRC"
    chk "OHOS_03 打包库真实运行" 1
fi

# OHOS_04: 打包运行时库符号完整性（C 可调用导出存在，无空壳包）
if [ -n "$READELF" ]; then
    bad=0
    syms=$("$READELF" -Ws "$LIBDIR/libm2pim.so" 2>/dev/null)
    for sym in m2pim_Builtins_strlen m2pim_Builtins_strcmp; do
        echo "$syms" | grep -q " $sym$" || { echo "  missing symbol: $sym"; bad=1; }
    done
    iso_syms=$("$READELF" -Ws "$LIBDIR/libm2iso.so" 2>/dev/null)
    for sym in m2iso_CharClass_IsLetter m2iso_CharClass_IsNumeric m2iso_CharClass_IsUpper; do
        echo "$iso_syms" | grep -q " $sym$" || { echo "  missing symbol: $sym"; bad=1; }
    done
    chk "OHOS_04 运行时库导出符号完整（strlen/strcmp/CharClass）" "${bad:-0}"
else
    chk "OHOS_04 运行时库导出符号完整" 1
fi

echo "--- libgm2 OHOS 专项: $([ $fail = 0 ] && echo ALL PASS || echo FAILED) ---"
exit $fail
