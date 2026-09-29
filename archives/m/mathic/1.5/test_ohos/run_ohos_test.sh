#!/bin/sh
# test_ohos/run_ohos_test.sh — mathic 1.5 HarmonyOS 专项验证（自包含）
#
# 对最终 Conan 包做独立 OHOS 专项检查，区别于上游 gtest 套件与
# test_package 消费者用例：
#   S1  aarch64 ELF / 宿主路径泄漏检查（libmathic.a 须为 ELF64 AArch64，
#       且不含 /storage、/home、/Users 等构建机绝对路径）
#   S2  编译并运行 ohos_special_test：aarch64 宽度/对齐契约、
#       bionic std::thread 确定性、MATHIC_VERSION_STRING=="1.5"
#
# 用法：sh run_ohos_test.sh <已安装包目录> [cxx] [ar]
# 退出码：0=全部通过；非 0=有失败（打印首个错误）。
set -u
PKG="${1:-}"
CXX="${2:-clang++}"
AR="${3:-llvm-ar}"
[ -n "$PKG" ] && [ -d "$PKG" ] || { echo "usage: $0 <installed-package-dir> [cxx] [ar]"; exit 2; }
LIB="$PKG/lib/libmathic.a"
INC="$PKG/include"
MEM_INC="$PKG/../../../b/mathi5ebe4ba20a5f1/p/../../../.."  # placeholder, overridden below
[ -f "$LIB" ] || { echo "FAIL: $LIB not found"; exit 2; }

fail=0
chk() { # $1=name $2=result
    if [ "$2" = "0" ]; then echo "PASS: $1"; else echo "FAIL: $1"; fail=1; fi
}

echo "--- mathic 1.5 HarmonyOS 专项验证 (pkg=$PKG) ---"

# S1a: aarch64 ELF（静态库首个成员即可，同一 archive 全为 arm64 目标）
readelf -h "$LIB" 2>/dev/null | grep -q "AArch64" && r=0 || r=1
chk "S1a libmathic.a 为 aarch64 (ELF64 AArch64)" "$r"

# S1b: 宿主绝对路径泄漏
if strings "$LIB" | grep -qE '/storage/|/home/|/Users/'; then
    echo "  leak: $(strings "$LIB" | grep -E '/storage/|/home/|/Users/' | head -1)"
    chk "S1b 无宿主绝对路径泄漏" 1
else
    chk "S1b 无宿主绝对路径泄漏" 0
fi

# 依赖 memtailor 头/库目录（在 Conan 包缓存根下定位，与 test_package 注入方式一致）
CONAN_P_ROOT="$(dirname "$(dirname "$(dirname "$PKG")")")"   # .../.conan2/p
MEM_INC_DIR=""
for cand in "$CONAN_P_ROOT"/*/p/include/memtailor.h; do
    [ -f "$cand" ] && MEM_INC_DIR=$(dirname "$cand") && break
done
[ -n "$MEM_INC_DIR" ] || MEM_INC_DIR="$INC"
MEM_A=""
for cand in "$CONAN_P_ROOT"/*/p/lib/libmemtailor.a; do
    [ -f "$cand" ] && MEM_A="$cand" && break
done
if [ -z "$MEM_A" ]; then
    echo "FAIL: libmemtailor.a not found beside mathic package"
    exit 2
fi

# S2: 编译并运行专项测试
SRC="$(dirname "$0")/ohos_special_test.cpp"
EXE="$(dirname "$0")/ohos_special_test.bin"
"$CXX" -std=c++17 -O1 -I"$INC" -I"$MEM_INC_DIR" "$SRC" \
    -L"$PKG/lib" -lmathic -L"$(dirname "$MEM_A")" -lmemtailor -pthread -o "$EXE" 2>ohos_special_build.err
if [ $? -eq 0 ]; then
    "$EXE" > ohos_special_run.log 2>&1
    rc=$?
    echo "--- ohos_special_test output ---"
    cat ohos_special_run.log
    echo "--- end ---"
    chk "S2 ohos_special_test 编译运行 (rc=$rc)" "$([ $rc -eq 0 ] && echo 0 || echo 1)"
else
    echo "FAIL: ohos_special_test compile failed:"
    cat ohos_special_build.err
    fail=1
fi

if [ "$fail" = "0" ]; then
    echo "ALL PASS: mathic 1.5 HarmonyOS special test (S1a/S1b/S2) passed"
fi
exit "$fail"
