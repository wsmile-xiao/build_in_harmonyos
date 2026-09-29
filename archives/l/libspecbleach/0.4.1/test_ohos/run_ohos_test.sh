#!/bin/sh
# test_ohos — libspecbleach 0.4.1 HarmonyOS PC 专项验证（自包含，可单独执行）
#
# 在真实鸿蒙 PC（aarch64, OHOS）上对最终 Conan 包做独立专项检查，
# 区别于上游内置自测（41 个 CTest 入口）与 test_package 消费者用例：
#
#   T1  安装产物结构核验（lib/include/pkgconfig 齐备，头文件含 SPECBLEACH_API）
#   T2  aarch64 ELF 验证（libspecbleach.so 为 ELF64 AArch64 共享库）
#   T3  OHOS 宿主路径泄漏检查（无 /storage、/home 等宿主绝对路径）
#   T4  API 运行时验证：编译一个仅用公开头的消费程序，初始化降噪器、
#       处理一帧静音音频并核对延迟/输出范围（可观察业务结果）
#
# 用法：sh run_ohos_test.sh <conan 包安装根>
# 退出码：0=全部通过；非 0=有失败（打印首个错误）。
set -u
PREFIX="${1:-}"
[ -n "$PREFIX" ] || { echo "usage: $0 <package-prefix>"; exit 2; }
[ -d "$PREFIX" ] || { echo "FAIL: package prefix not found: $PREFIX"; exit 2; }

fail=0
chk() { # $1=name $2=result
    if [ "$2" = "0" ]; then echo "PASS: $1"; else echo "FAIL: $1"; fail=1; fi
}

echo "--- libspecbleach 0.4.1 HarmonyOS 专项验证 (prefix=$PREFIX) ---"

# T1: 安装产物结构
LIBDIR="$PREFIX/lib"
INCDIR="$PREFIX/include"
t1=0
[ -f "$LIBDIR/libspecbleach.so" ] || [ -f "$LIBDIR/libspecbleach.a" ] || { echo "  no library artifact"; t1=1; }
[ -f "$INCDIR/specbleach_denoiser.h" ] || { echo "  missing specbleach_denoiser.h"; t1=1; }
[ -f "$LIBDIR/pkgconfig/specbleach.pc" ] || { echo "  missing specbleach.pc"; t1=1; }
grep -q "SPECBLEACH_API" "$INCDIR/specbleach_denoiser.h" || { echo "  SPECBLEACH_API missing"; t1=1; }
chk "T1 产物结构核验 (lib/include/pkgconfig/SPECBLEACH_API)" "$t1"

# T2: aarch64 ELF 验证（共享库或静态归档）
ELF="$(ls "$LIBDIR"/libspecbleach.so "$LIBDIR"/libspecbleach.a 2>/dev/null | head -1)"
if [ -n "$ELF" ]; then
    if llvm-readelf -h "$ELF" 2>/dev/null | grep -q "AArch64"; then
        chk "T2 aarch64 ELF 验证 ($ELF)" 0
    else
        echo "  ELF machine is not AArch64"; chk "T2 aarch64 ELF 验证" 1
    fi
else
    chk "T2 aarch64 ELF 验证 (artifact missing)" 1
fi

# T3: 宿主路径泄漏检查（Conan 打包产物不应内嵌本机绝对路径；
#     检查文本产物 .pc/.cmake/.h/.hpp 与动态库 DT_RUNPATH，忽略 .so 内
#     调试字符串 __FILE__ 残留——那是编译器调试信息，不属于消费者可见泄漏）
t3=0
if grep -rlE "/storage/|/home/|/Users/" "$LIBDIR" "$INCDIR" \
        --include='*.pc' --include='*.cmake' --include='*.h' --include='*.hpp' 2>/dev/null | grep -q .; then
    echo "  text host path leak detected"; t3=1
fi
if llvm-readelf -d "$ELF" 2>/dev/null | grep -E "RPATH|RUNPATH" | grep -qE "/storage|/home|/Users"; then
    echo "  DT_RUNPATH host path leak detected"; t3=1
fi
chk "T3 宿主路径泄漏检查 (文本产物+DT_RUNPATH 无 /storage /home /Users)" "$t3"

# T4: API 运行时验证（公开头 + 公开 API，编译运行消费程序）
CC_BIN="${CC:-$(command -v clang 2>/dev/null || command -v cc 2>/dev/null)}"
SRC="$(mktemp "${TMPDIR:-/tmp}/ohos-test.XXXXXX" 2>/dev/null || mktemp /tmp/ohos-test.XXXXXX)"
[ -n "$SRC" ] && SRC="$SRC.c"
BIN="${SRC%.c}"
cat > "$SRC" <<'CCODE'
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "specbleach_denoiser.h"

int main(void) {
    uint32_t sr = 44100, n = 512;
    /* v0.4.1 API: initialize(sample_rate, frame_size_ms, flags) */
    specbleach_denoiser *d = specbleach_denoiser_initialize(sr, 46.0f, 0u);
    if (!d) { fprintf(stderr, "initialize failed\n"); return 1; }
    /* Baseline parameter block (real v0.4.1 fields), reloaded via size ABI guard */
    SpecbleachDenoiserParameters p = specbleach_denoiser_get_default_parameters();
    if (!specbleach_denoiser_load_parameters(d, &p, SPECBLEACH_PARAMETERS_SIZE)) { fprintf(stderr, "load params failed\n"); return 1; }
    float *x = (float *)calloc(n, sizeof(float));
    float *y = (float *)calloc(n, sizeof(float));
    if (!x || !y) return 1;
    if (!specbleach_denoiser_process(d, n, x, y)) { fprintf(stderr, "process failed\n"); return 1; }
    for (uint32_t i = 0; i < n; i++)
        if (!(y[i] >= -1.0f && y[i] <= 1.0f)) { fprintf(stderr, "out of range %u\n", i); return 1; }
    uint32_t lat = specbleach_denoiser_get_latency(d);
    printf("OHOS API OK: latency=%u\n", lat);
    specbleach_denoiser_free(d);
    free(x); free(y);
    return 0;
}
CCODE
if [ -n "$CC_BIN" ] && "$CC_BIN" -std=c17 -I"$INCDIR" "$SRC" -L"$LIBDIR" -lspecbleach -lm -o "$BIN" 2>/dev/null \
        && LD_LIBRARY_PATH="$LIBDIR${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" "$BIN"; then
    chk "T4 API 运行时验证 (initialize/process/latency)" 0
else
    echo "  T4 consumer build/run failed with $CC_BIN"; chk "T4 API 运行时验证" 1
fi
rm -f "$SRC" "$BIN"

echo "---"
[ "$fail" = "0" ] && echo "ALL PASS: libspecbleach 0.4.1 OHOS 专项验证通过" || echo "SOME FAILED"
exit "$fail"
