#!/bin/sh
# consumer_use_case.sh — libgm2 16.1.1 消费者用例驱动脚本（自包含）
#
# 消费者用例语义：模拟上层业务组件/应用，仅通过库已安装/导出的公开接口
# （Modula-2 运行时 API：m2iso_CharClass_* / m2pim_Builtins_*，C 可调用）
# 使用该三方库，验证第三方使用者能够调用并得到可观察结果。libgm2 为
# 运行时库包（无 CLI 可执行文件），公开 API = 运行时库的 C 调用接口；
# 不包含库私有头、不调用内部符号、不复用内部测试构建目录。
#
# 用例场景：上层应用（如配置清单预检报告器）用打包的运行时库对一段
# 文本配置清单做字符分类统计、长度计算与键值一致性校验，输出报告。
# 本脚本自包含完成 编译 → 链接 → 运行 → 核验输出 全链路。
#
# 用法：sh consumer_use_case.sh <共享库目录> [编译器，默认 clang]
# 退出码：0=全部通过；非 0=失败。
set -u
LIBDIR="${1:-}"
CC="${2:-clang}"
[ -n "$LIBDIR" ] && [ -d "$LIBDIR" ] || { echo "usage: $0 <libdir> [compiler]"; exit 2; }
[ -f "$LIBDIR/libm2iso.so" ] || { echo "FAIL: libm2iso.so not found in $LIBDIR"; exit 2; }

HERE=$(dirname "$0")
WORK=$(mktemp -d "${TMPDIR:-/tmp}/libgm2-consumer.XXXXXX") || exit 2
trap 'rm -rf "$WORK"' EXIT

fail=0
chk() { if [ "$2" = "0" ]; then echo "PASS: $1"; else echo "FAIL: $1"; fail=1; fi }

echo "--- 消费者用例 (libgm2 16.1.1, libdir=$LIBDIR) ---"

# 编译：真实业务程序链接打包的运行时库（--allow-shlib-undefined 同
# test_package 口径：运行时 .so 留有弱 libc 符号，GNU ld 容忍）。
if "$CC" -O2 -Wl,--allow-shlib-undefined \
    -L"$LIBDIR" -lm2iso -lm2pim -lm \
    "$HERE/consumer_use_case.c" -o "$WORK/consumer" 2>"$WORK/cc.log"; then
    chk "C0 消费者程序编译+链接 (clang -lm2iso -lm2pim)" 0
else
    echo "  $(head -5 "$WORK/cc.log")"
    chk "C0 消费者程序编译+链接" 1
fi

[ -f "$WORK/consumer" ] || { echo "--- 消费者用例: FAILED (no binary) ---"; exit $fail; }

# 运行：LD_LIBRARY_PATH 指向打包的共享库目录（真实加载运行时）。
out=$(LD_LIBRARY_PATH="$LIBDIR" "$WORK/consumer" 2>&1); rc=$?
if [ "$rc" = "0" ]; then
    chk "C1 消费者业务流程执行 (rc=0)" 0
else
    echo "  rc=$rc out=$(echo "$out" | head -3)"
    chk "C1 消费者业务流程执行" 1
fi

# C2: 统计结果可观察核验（与手工验算期望值一致：22/5/10/33）
if echo "$out" | grep -qE 'letters=22 digits=5 upper=10 total=33 key_eq=1 key_ne=1'; then
    chk "C2 统计报告与期望一致 (letters=22 digits=5 upper=10 total=33, key_eq=1, key_ne=1)" 0
else
    echo "  out=$out"
    chk "C2 统计报告与期望一致" 1
fi

# C3: 成功标记输出核验
if echo "$out" | grep -q 'consumer-ok'; then
    chk "C3 输出 consumer-ok 成功标记" 0
else
    echo "  out=$out"
    chk "C3 输出 consumer-ok 成功标记" 1
fi

echo "--- 消费者用例: $([ $fail = 0 ] && echo ALL PASS || echo FAILED) ---"
exit $fail
