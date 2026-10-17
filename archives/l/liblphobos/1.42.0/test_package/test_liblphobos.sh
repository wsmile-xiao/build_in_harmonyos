#!/bin/sh
# R34 反空壳消费者用例（鸿蒙新增）：真实编译并**实际运行**一个链接 liblphobos
# 共享库的 D 程序——验证 libphobos2-ldc-shared.so.112 + libdruntime-ldc-shared.so.112
# 在 OHOS 上的完整可用性（编译→签名→加载→运行→输出断言）。
#
# 用法： test_liblphobos.sh <ldc2 路径> <liblphobos 包目录> <hello_phobos.d 所在目录>
#
# 覆盖五件事（缺一不可）：
#   ① ldc2 --version                        —— 编译器可用
#   ② ldc2 -conf= 编译消费者程序            —— **完全脱离 ldc2 默认配置**：
#      import 头与库全部指向 liblphobos 包（-I<pkg>/include/d -L-L<pkg>/lib），
#      -defaultlib=phobos2-ldc-shared,druntime-ldc-shared 显式链接**本包共享库**
#      （非 ldc 包内的静态库）——这才构成对 liblphobos 交付物的真实消费。
#   ③ OHOS 代码签名                          —— 不签名 exec 报 Permission denied/rc=126
#   ④ 实际运行并逐行断言输出                 —— 排序/map/格式化/JSON/字符串/时钟全链路
#   ⑤ 确认运行时实际加载的是本包 .so         —— LD_LIBRARY_PATH 指向本包 lib/
set -euo pipefail

LDC2="$1"
LIBPKG="$2"
SRCDIR="$3"

echo "=== ① ldc2 版本 ==="
"$LDC2" --version

echo "=== ② 编译消费者程序（链接 liblphobos 共享库）==="
WORK="$PWD/liblphobos-test-work"
rm -rf "$WORK" 2>/dev/null || true
mkdir -p "$WORK"
EXE="$WORK/hello_phobos"
INC="$LIBPKG/include/d"
LIB="$LIBPKG/lib"

# clang_passthrough shim：ldc2 spawn C 编译器驱动时把 stdout/stderr 接到无人
# 消费的管道，链接诊断写失败 → status 1（同 ldc 包实测）。shim 重定向 fd 到
# 日志文件后 execv 真 clang++。设备无 cc，链接驱动必须显式指定。
SHIM="$WORK/clang_passthrough"
/data/service/hnp/bin/clang -O2 -o "$SHIM" "$SRCDIR/clang_passthrough.c"
/data/service/hnp/bin/llvm-objcopy --remove-section .codesign "$SHIM" 2>/dev/null || true
/data/service/hnp/bin/binary-sign-tool sign -inFile "$SHIM" -outFile "$SHIM" -selfSign 1 2>/dev/null || true

if [ ! -f "$INC/std/stdio.d" ]; then
    echo "FAIL: liblphobos 包缺 import 头: $INC/std/stdio.d"
    exit 1
fi
if [ ! -f "$LIB/libphobos2-ldc-shared.so.112" ]; then
    echo "FAIL: liblphobos 包缺共享库: $LIB/libphobos2-ldc-shared.so.112"
    exit 1
fi

# -conf= 关闭 ldc2 默认配置（其默认指向 ldc 包自带的静态库），确保只消费本包；
# --gcc= 显式指定链接驱动（设备无 cc，且需 shim 绕开管道 fd 问题）
"$LDC2" -conf= \
    -I"$INC" \
    -defaultlib=phobos2-ldc-shared,druntime-ldc-shared \
    -L-L"$LIB" -L-lz -L-lm \
    --gcc="$SHIM" \
    -of="$EXE" \
    "$SRCDIR/hello_phobos.d"
if [ ! -f "$EXE" ]; then
    echo "FAIL: ldc2 未产出可执行文件"
    exit 1
fi

echo "=== ③ OHOS 代码签名 ==="
SIGNER="/data/service/hnp/bin/binary-sign-tool"
if [ -x "$SIGNER" ]; then
    OBJCOPY="/data/service/hnp/bin/llvm-objcopy"
    "$OBJCOPY" --remove-section .codesign "$EXE" 2>/dev/null || true
    "$SIGNER" sign -inFile "$EXE" -outFile "$EXE" -selfSign 1
    echo "signed: $EXE"
else
    echo "WARN: binary-sign-tool 不存在，跳过签名（非真机环境）"
fi

echo "=== ④ 运行并断言输出（LD_LIBRARY_PATH 追加本包 lib）==="
OUT="$(LD_LIBRARY_PATH="$LIB:${LD_LIBRARY_PATH:-}" "$EXE")"
echo "$OUT"

echo "$OUT" | grep -qF "sorted:  [1, 1, 2, 3, 4, 5, 6, 9]" \
    || { echo "FAIL: sorted 断言不通过"; exit 1; }
echo "$OUT" | grep -qF "doubled: [2, 2, 4, 6, 8, 10, 12, 18]" \
    || { echo "FAIL: doubled 断言不通过"; exit 1; }
echo "$OUT" | grep -qF "summary: n=8 max=9" \
    || { echo "FAIL: summary 断言不通过"; exit 1; }
echo "$OUT" | grep -qF "conv:    42" \
    || { echo "FAIL: conv 断言不通过"; exit 1; }
echo "$OUT" | grep -qF "json:    ohos/112/true" \
    || { echo "FAIL: json 断言不通过"; exit 1; }
echo "$OUT" | grep -qF "string:  PHOBOS-ON-OHOS" \
    || { echo "FAIL: string 断言不通过"; exit 1; }
echo "$OUT" | grep -qF "clock:   true" \
    || { echo "FAIL: clock 断言不通过"; exit 1; }

echo "=== ⑤ 运行时库加载确认（DT_NEEDED 硬断言）==="
# 优先用 llvm-readelf 读可执行文件的动态段：两个 soname 必须出现在 DT_NEEDED
# （配合 ④ 的 LD_LIBRARY_PATH 指向本包 lib/，即证实加载的是本包交付的 .so）。
READELF="/data/service/hnp/bin/llvm-readelf"
if [ -x "$READELF" ]; then
    NEEDED="$("$READELF" --dynamic "$EXE" 2>/dev/null | grep NEEDED || true)"
    echo "$NEEDED"
    echo "$NEEDED" | grep -qF "libphobos2-ldc-shared.so.112" \
        || { echo "FAIL: DT_NEEDED 未含 libphobos2-ldc-shared.so.112"; exit 1; }
    echo "$NEEDED" | grep -qF "libdruntime-ldc-shared.so.112" \
        || { echo "FAIL: DT_NEEDED 未含 libdruntime-ldc-shared.so.112"; exit 1; }
    echo "runtime NEEDED: 本包两个共享库均在动态段中"
else
    # 非 OHOS 环境（无 llvm-readelf）退回 ldd；两工具皆不可用则视为失败。
    ldd "$EXE" 2>/dev/null | grep -E "phobos|druntime" \
        || { echo "FAIL: 无法验证运行时加载（llvm-readelf 与 ldd 均不可用）"; exit 1; }
fi

echo "PASS: liblphobos 消费者用例 7/7 断言全部通过"
