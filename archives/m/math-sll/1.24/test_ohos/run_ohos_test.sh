#!/bin/sh
# test_ohos — math-sll 1.24 HarmonyOS PC 专项验证（自包含，可单独执行）
#
# 在真实鸿蒙 PC（aarch64, OHOS）上对最终 Conan 包做独立专项检查，
# 区别于 test_package 消费者用例（前者由 conan create 驱动）：
#
#   T1  aarch64 静态库归档验证（math-sll.a 内成员为 ELF64 AArch64）
#   T2  宿主路径泄漏检查（构建机 /storage、/home 等绝对路径不得进入产物）
#   T3  真实消费者程序编译+链接+运行：仅使用已安装的公开头文件 math-sll.h
#       与静态库 libmath-sll.a，调用定点数公开 API（dbl2sll/sllmul/sllsqrt）
#       并校验可观察数值结果
#
# 用法：sh run_ohos_test.sh <已安装包根目录>
# 退出码：0=全部通过；非 0=有失败（打印首个错误）。
set -u
PKG="${1:-}"
[ -n "$PKG" ] || { echo "usage: $0 <installed package dir>"; exit 2; }
[ -d "$PKG" ] || { echo "FAIL: package dir not found: $PKG"; exit 2; }

LIB="$PKG/lib/libmath-sll.a"
INC="$PKG/include/math-sll.h"
[ -f "$LIB" ] || { echo "FAIL: library not found: $LIB"; exit 2; }
[ -f "$INC" ] || { echo "FAIL: header not found: $INC"; exit 2; }

fail=0
chk() { # $1=name $2=result
    if [ "$2" = "0" ]; then echo "PASS: $1"; else echo "FAIL: $1"; fail=1; fi
}

echo "--- math-sll HarmonyOS 专项验证 (pkg=$PKG) ---"

# T1: aarch64 归档成员
TMPD="${TMPDIR:-/storage/Users/currentUser/tmp}/math-sll-ohos-$$"
mkdir -p "$TMPD" && cd "$TMPD"
llvm-ar x "$LIB"
if file math-sll.o 2>/dev/null | grep -qE 'AArch64|arm64'; then
    chk "T1 aarch64 静态库归档 (AArch64)" 0
else
    echo "  arch: $(file math-sll.o 2>&1)"
    chk "T1 aarch64 静态库归档" 1
fi

# T2: 宿主路径泄漏（/storage /home 不得进入 .a 与 .h）
if strings "$LIB" "$INC" | grep -qE '/storage/|/home/|/Users/'; then
    echo "  leak: $(strings "$LIB" "$INC" | grep -E '/storage/|/home/|/Users/' | head -1)"
    chk "T2 无宿主绝对路径泄漏" 1
else
    chk "T2 无宿主绝对路径泄漏" 0
fi

# T3: 独立消费者程序（仅公开 API）
cat > ohos_consumer.c <<'EOF'
#include <stdio.h>
#include <math.h>
#include "math-sll.h"
int main(void) {
    sll a = dbl2sll(1.5);
    sll b = dbl2sll(2.0);
    sll p = sllmul(a, b);          /* 1.5 * 2.0 = 3.0 */
    sll r = sllsqrt(dbl2sll(4.0)); /* sqrt(4) = 2.0 */
    if (fabs(sll2dbl(p) - 3.0) > 1e-9) return 1;
    if (fabs(sll2dbl(r) - 2.0) > 1e-6) return 2;
    printf("math-sll consumer OK: mul=%.6f sqrt=%.6f\n", sll2dbl(p), sll2dbl(r));
    return 0;
}
EOF
clang -I"$PKG/include" ohos_consumer.c "$LIB" -o ohos_consumer -lm 2>compile.err
if [ $? -ne 0 ]; then
    echo "  compile: $(head -3 compile.err)"
    chk "T3 消费者编译链接" 1
else
    ./ohos_consumer > run.out 2>&1
    rc=$?
    if [ "$rc" = "0" ]; then
        chk "T3 消费者编译链接并运行 (rc=0)" 0
    else
        echo "  run rc=$rc: $(cat run.out)"
        chk "T3 消费者运行" 1
    fi
fi

cd - >/dev/null 2>&1
rm -rf "$TMPD"
echo "--- math-sll OHOS 专项: $([ $fail = 0 ] && echo ALL PASS || echo FAILED) ---"
exit $fail