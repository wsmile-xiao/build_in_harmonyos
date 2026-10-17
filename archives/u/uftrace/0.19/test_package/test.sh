#!/bin/sh
# test.sh — uftrace 0.19 验证
#   1) 真正执行 uftrace --version（验证产物可执行，而非仅存在性）
#   2) 5 个 libmcount 插桩库齐全
# Usage: sh test.sh <uftrace-bin> <lib/uftrace-dir>
set -eu

BIN="${1:?usage: test.sh <uftrace-bin> <lib-uftrace-dir>}"
LIBDIR="${2:?}"

if [ ! -f "$BIN" ]; then
    echo "FAIL: uftrace binary not found: $BIN"
    exit 1
fi

# 真正执行被测产物；build() 已证明签名后的 OHOS 二进制可在 Conan
# subprocess 链中执行（单元测试 93/96 即由此执行），故此处不再只做存在性判断。
"$BIN" --version
echo "PASS: uftrace --version executed"

if [ ! -d "$LIBDIR" ]; then
    echo "FAIL: lib/uftrace dir missing: $LIBDIR"
    exit 1
fi

for lib in libmcount.so libmcount-nop.so libmcount-fast.so libmcount-single.so libmcount-fast-single.so; do
    if [ ! -f "$LIBDIR/$lib" ]; then
        echo "FAIL: missing instrumentation library: $lib"
        exit 1
    fi
    echo "PASS: present $lib"
done

echo "ALL uftrace checks passed."
