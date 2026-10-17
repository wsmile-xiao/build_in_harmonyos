#!/bin/sh
# libgcobol 端到端验证（仅在 GCOBOL 前端可用时执行）：
# 用 GCOBOL 前端编译真实 COBOL 程序，链接「被测包」libgcobol（LIBGCOBOL_LIBDIR），
# ELF 签名后运行并断言数值运算 / 定长浮点 / 字符串 / 条件 / 循环 / 内建函数全部正确。
#
# 由 test_package/conanfile.py 传入（消费被测包，而非真机 build tree）：
#   GCOBOL             — GCOBOL 前端绝对路径（本机适配结果，见 feat/gcobol-16.1.0）
#   LIBGCOBOL_LIBDIR   — 被测包 libgcobol 的 lib 目录（conan create 产出制品）
#
# 前端/被测包 libdir 缺失时本脚本退出非零（test_package 已先探测并在前端不可用时
# 如实输出 [SKIP]；本脚本被直接调用时则明确失败，绝不静默 exit 0 伪造通过）。
set -e

export TMPDIR="${TMPDIR:-/data/storage/el2/base/cache}"
export GCOBOL_TEMPDIR="${GCOBOL_TEMPDIR:-/data/storage/el2/base/cache/}"

GCOBOL="${GCOBOL:-}"
if [ -z "$GCOBOL" ]; then
  echo "test.sh: GCOBOL 前端不可用，端到端 COBOL 程序测试无法执行" >&2
  exit 1
fi
LIBGCOBOL_LIBDIR="${LIBGCOBOL_LIBDIR:-}"
if [ -z "$LIBGCOBOL_LIBDIR" ]; then
  echo "test.sh: 缺少 LIBGCOBOL_LIBDIR（被测包 lib 目录），拒绝执行" >&2
  exit 1
fi

# 以下为 GCOBOL 前端（编译器）的 GCC 驱动支持目录，来自本机适配结果
# （feat/gcobol-16.1.0 build tree），是编译 COBOL 程序所需的 -B 启动文件与
# 目标 libgcc，不是被测库；被测库 libgcobol 一律从 $LIBGCOBOL_LIBDIR 链接/加载。
OBJ=/storage/Users/currentUser/gcobol-obj
SYSR=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot
LIBARCH="$SYSR/usr/lib/aarch64-linux-ohos"
XML2=/storage/Users/currentUser/libxml2-fixed

"$GCOBOL" -mmusl \
  -B"$OBJ/gcc/" -B"$OBJ/aarch64-linux-ohos/libgcobol/" -B"$LIBARCH/" -B/data/service/hnp/bin/ \
  --sysroot="$SYSR" \
  -L"$LIBGCOBOL_LIBDIR" -L"$OBJ/aarch64-linux-ohos/libgcc" \
  -L"$LIBARCH" -L"$XML2" -L/storage/Users/currentUser/libstdc-stub \
  -Wl,-rpath,"$LIBGCOBOL_LIBDIR" -Wl,-rpath,"$XML2" -Wl,-rpath-link,"$XML2" \
  -o lg_probe test_program.cob

# OHOS 动态链接器只加载带 .codesign 的 ELF
cp -p lg_probe lg_probe.unsigned
/data/service/hnp/bin/binary-sign-tool sign -inFile lg_probe.unsigned -outFile lg_probe.signed -selfSign 1 >/dev/null 2>&1
mv lg_probe.signed lg_probe
rm -f lg_probe.unsigned
chmod 755 lg_probe

LD_LIBRARY_PATH="$LIBGCOBOL_LIBDIR:$XML2${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" \
  ./lg_probe > lg_out.txt

grep -q 'POWER:0000000100' lg_out.txt
grep -q 'FIXED:07.00' lg_out.txt
grep -q 'STR:HELLO-LIBGCOBOL' lg_out.txt
grep -q 'IF:OK' lg_out.txt
grep -q 'SUM1-5:015' lg_out.txt
grep -q 'MAX:8' lg_out.txt
grep -q 'MIN:-14' lg_out.txt

echo "libgcobol: GCOBOL 前端编译 + 链接被测包 libgcobol + 运行 COBOL 程序断言全部通过"
