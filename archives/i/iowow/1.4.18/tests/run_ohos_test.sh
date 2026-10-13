#!/bin/sh
# test_ohos — iowow 1.4.18 HarmonyOS PC 专项验证（自包含，可单独执行）
#
# 在真实鸿蒙 PC（aarch64, OHOS/musl）上对最终 Conan 包产物做独立专项检查，
# 区别于上游 CUnit 测试（功能回归）与 test_package（消费者 API 验证）：
#
#   T1  静态库 ELF 验证：libiowow-1.a 为 ELF64 AArch64 REL（可重定位）
#   T2  musl 纯净性：无 GLIBC 版本化符号（@@GLIBC / __libc_ / __isoc99_）
#   T3  无宿主 RPATH/RUNPATH 泄漏（静态库检 archive 成员 dynamic 段）
#   T4  无宿主绝对路径泄漏（/storage /home /Users 不进入产物）
#   T5  真实运行：用 OHOS 工具链编译 harmonyos_test.c 链接最终包静态库，
#       在 OHOS 上运行，验证 mmap/flock/fsync/线程原子 + iwkv 全生命周期
#
# 用法：sh run_ohos_test.sh <包根目录> [工作目录]
#   包根目录 = Conan 包安装前缀（含 include/ lib/）
# 退出码：0=全部通过；非 0=有失败。
set -u

PKG="${1:-}"
WORK="${2:-$(pwd)}"
[ -n "$PKG" ] || { echo "usage: $0 <package-prefix> [workdir]"; exit 2; }
[ -d "$PKG/include/iowow" ] || { echo "FAIL: $PKG/include/iowow not found"; exit 2; }

CLANG="${CC:-/storage/Users/currentUser/usr/local/bin/clang}"
LIB="$PKG/lib/libiowow-1.a"
[ -f "$LIB" ] || { echo "FAIL: $LIB not found"; exit 2; }

fail=0
chk() { # $1=name $2=result
    if [ "$2" = "0" ]; then echo "PASS: $1"; else echo "FAIL: $1"; fail=1; fi
}

TESTSRC="$(dirname "$0")/harmonyos_test.c"
BIN="$WORK/harmonyos_test_iowow18"

echo "--- iowow 1.4.18 HarmonyOS PC 专项验证 (pkg=$PKG) ---"

# T1: 静态库 ELF64 AArch64（archive 中每个成员都应为 AArch64 REL）
readelf -h "$LIB" 2>/dev/null | grep -q "Class:.*ELF64" && r=0 || r=1
chk "T1a libiowow-1.a is ELF64" "$r"
readelf -h "$LIB" 2>/dev/null | grep -q "Machine:.*AArch64" && r=0 || r=1
chk "T1b libiowow-1.a machine is AArch64" "$r"

# T2: musl 纯净 — 无 GLIBC 版本化符号（动态符号表不存在于 REL，查符号名）
if nm "$LIB" 2>/dev/null | grep -qE "@@GLIBC|__libc_start_main|__isoc99_"; then
    echo "  leak: $(nm "$LIB" 2>/dev/null | grep -E "@@GLIBC|__libc_start_main|__isoc99_" | head -1)"
    chk "T2 无 GLIBC 版本化符号 (musl pure)" 1
else
    chk "T2 无 GLIBC 版本化符号 (musl pure)" 0
fi

# T3: 无宿主 RPATH/RUNPATH（静态库成员为 REL 无 dynamic 段；链接产物统一在 T4/T5 复查）
if readelf -d "$LIB" 2>/dev/null | grep -qE "RPATH|RUNPATH"; then
    chk "T3 无宿主 RPATH/RUNPATH" 1
else
    chk "T3 无宿主 RPATH/RUNPATH" 0
fi

# T4: 无宿主绝对路径泄漏
if strings -a "$LIB" | grep -qE '/storage/|/home/|/Users/'; then
    echo "  leak: $(strings -a "$LIB" | grep -E '/storage/|/home/|/Users/' | head -1)"
    chk "T4 无宿主绝对路径泄漏" 1
else
    chk "T4 无宿主绝对路径泄漏" 0
fi

# T5: 真实运行 — 编译 + 链接最终包 + 在 OHOS 上执行
echo "T5: compiling harmonyos_test.c with OHOS toolchain..."
if "$CLANG" -std=gnu11 -O2 -DIW_STATIC \
     -I"$PKG/include" "$TESTSRC" "$LIB" -lm -pthread -o "$BIN" 2>"$WORK/ohos-build.log"; then
    chk "T5a OHOS clang 编译链接最终包静态库" 0
else
    cat "$WORK/ohos-build.log"
    chk "T5a OHOS clang 编译链接最终包静态库" 1
fi

# T5b: 可执行产物 ELF/平台复查（真实运行前先验形）
readelf -h "$BIN" 2>/dev/null | grep -q "Class:.*ELF64" && r=0 || r=1
chk "T5b 可执行产物为 ELF64" "$r"
readelf -h "$BIN" 2>/dev/null | grep -q "Machine:.*AArch64" && r=0 || r=1
chk "T5c 可执行产物为 AArch64" "$r"
if readelf -d "$BIN" 2>/dev/null | grep -E "RPATH|RUNPATH" | grep -qE '/storage|/home|/Users'; then
    chk "T5d 无宿主 RPATH/RUNPATH" 1
else
    chk "T5d 无宿主 RPATH/RUNPATH" 0
fi
if strings -a "$BIN" | grep -qE '/storage/|/home/|/Users/'; then
    echo "  leak: $(strings -a "$BIN" | grep -E '/storage/|/home/|/Users/' | head -1)"
    chk "T5e 无宿主绝对路径泄漏" 1
else
    chk "T5e 无宿主绝对路径泄漏" 0
fi

# T5f: 真实运行（平台能力 + 存储引擎全生命周期）
if "$BIN" > "$WORK/ohos-run.log" 2>&1; then
    chk "T5f harmonyos_test 运行退出码 0" 0
    grep -c "^PASS:" "$WORK/ohos-run.log" | while read n; do
        echo "      ($n PASS checks in run log)"
    done
else
    rc=$?
    cat "$WORK/ohos-run.log"
    chk "T5f harmonyos_test 运行退出码 0" "$rc"
fi

echo "--- iowow 1.4.18 OHOS 专项: $([ $fail = 0 ] && echo ALL PASS || echo FAILED) ---"
exit $fail
