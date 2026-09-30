#!/bin/sh
# test_package 消费验证：用 gcobol 前端编译 COBOL 程序，链接 libgcobol，
# 运行并断言 COMPUTE 10**2 输出 100。
set -e

# OHOS 特有运行时要求：
#   - TMPDIR 用 tmpfs（config/词法器临时文件，HMDFS 上 mktemp 会失败）
#   - GCOBOL_TEMPDIR 让 cobol1 的词法/符号表临时文件落在可写 tmpfs
#   - --sysroot 指向 OHOS sysroot（缺了 cobol1 落到非 OHOS 默认头文件）
export TMPDIR="${TMPDIR:-/data/storage/el2/base/cache}"
export GCOBOL_TEMPDIR="${GCOBOL_TEMPDIR:-/data/storage/el2/base/cache/}"
export OHOS_SYSROOT="${OHOS_SYSROOT:-/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot}"

gcobol -mmusl --sysroot="$OHOS_SYSROOT" -o test_probe test_program.cob
./test_probe > test_out.txt
grep -q '100' test_out.txt
echo "gcobol: COBOL compile+run 10**2=100 PASS"
