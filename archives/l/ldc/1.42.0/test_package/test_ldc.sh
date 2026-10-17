#!/bin/sh
# R34 反空壳测试：真实编译并**实际运行**一个使用 druntime + Phobos 的 D 程序。
#
# 用法： test_ldc.sh <ldc2 路径> <hello.d 所在目录>
#
# 覆盖四件事（缺一不可）：
#   ① ldc2 --version            —— 编译器自身可执行（含所基于的 DMD 前端与 LLVM 版本）
#   ② ldc2 真实编译 hello.d     —— 用到 std.stdio/std.algorithm/std.range/std.format/std.conv，
#                                  即同时覆盖 druntime 与 Phobos 两个运行时库
#   ③ OHOS 代码签名             —— 不签名会被内核拒绝 exec（Permission denied / rc=126）
#   ④ 实际运行并断言输出         —— 只看"编译通过"不算数，必须核对运行结果
set -eu

LDC2="$1"
SRCDIR="$2"

echo "=== ① ldc2 版本 ==="
"$LDC2" --version

echo "=== ② 编译 hello.d（druntime + Phobos）==="
WORK="$PWD/ldc-test-work"
rm -rf "$WORK"
mkdir -p "$WORK"
EXE="$WORK/hello"
# -L-lz -L-lm：Phobos 的 std.zlib 与数学函数需要这两个库
"$LDC2" "$SRCDIR/hello.d" -of="$EXE" -L-lz -L-lm
if [ ! -f "$EXE" ]; then
    echo "FAIL: ldc2 未产出可执行文件"
    exit 1
fi

echo "=== ③ OHOS 代码签名 ==="
SIGNER="/data/service/hnp/bin/binary-sign-tool"
if [ -x "$SIGNER" ]; then
    "$SIGNER" sign -inFile "$EXE" -outFile "$EXE" -selfSign 1
else
    echo "FAIL: 未找到 binary-sign-tool（OHOS 上未签名的 ELF 无法 exec）"
    exit 1
fi
chmod +x "$EXE"

echo "=== ④ 实际运行并断言输出 ==="
OUT="$WORK/hello.out"
"$EXE" > "$OUT" 2>&1
cat "$OUT"

grep -F "sorted:  [1, 1, 2, 3, 4, 5, 6, 9]" "$OUT"
grep -F "doubled: [2, 2, 4, 6, 8, 10, 12, 18]" "$OUT"
grep -F "summary: n=8 max=9" "$OUT"
grep -F "conv:    42" "$OUT"

echo "OK: ldc2 编译并真实运行 D 程序成功（druntime + Phobos 均已验证）"
