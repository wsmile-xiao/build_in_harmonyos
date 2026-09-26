#!/bin/sh
# uncrustify 0.79.0 — test_package 消费者用例（鸿蒙特有测试行，13 条断言）
#
# usage: test.sh <bin-dir> <recipe-dir> <work-dir>
#
# 计数口径：TOTAL = PASS + FAIL；SKIP 单列（宿主不满足前提时显式打印，
# 不冒充 PASS）。全部断言均为真实命令执行 + 真实输出核对，无空壳断言。
set -u

BIN=${1:-}
RECIPE=${2:-}
WORK=${3:-}

PASS=0
FAIL=0
SKIP=0

ok()  { PASS=$((PASS + 1)); printf 'PASS  %s\n' "$1"; }
no()  { FAIL=$((FAIL + 1)); printf 'FAIL  %s\n' "$1"; }
sk()  { SKIP=$((SKIP + 1)); printf 'SKIP  %s\n' "$1"; }
chk() { if [ "$1" -eq 0 ]; then ok "$2"; else no "$2"; fi; }
say() { printf '\n== %s\n' "$1"; }

if [ -z "$BIN" ] || [ -z "$RECIPE" ] || [ -z "$WORK" ]; then
  echo "usage: test.sh <bin-dir> <recipe-dir> <work-dir>" >&2
  exit 2
fi

mkdir -p "$WORK" || exit 2
cd "$WORK" || exit 2
rm -rf ./* 2>/dev/null

PATH="${BIN}:${PATH}"
export PATH
UNC=uncrustify

########################################################################
say "1. 版本与 help 冒烟"
ver_out=$("$UNC" --version 2>&1); ver_rc=$?
[ "$ver_rc" -eq 0 ]; chk $? "uncrustify --version 退出码为 0"
case "$ver_out" in
  *Uncrustify-0.79.0*) ok "--version 输出带版本标识 Uncrustify-0.79.0" ;;
  *) no "--version 输出缺版本标识: [$(printf '%s' "$ver_out" | head -1)]" ;;
esac
"$UNC" --help > help.txt 2>&1
[ $? -eq 0 ] && grep -q '^Usage:' help.txt
chk $? "--help 退出码为 0 且含 Usage 段"

########################################################################
say "2. 配置驱动的 C 格式化与黄金输出比对"
"$UNC" -c "$RECIPE/style.cfg" -f "$RECIPE/sample.c" -o out.c > fmt.log 2>&1
chk $? "按 style.cfg 格式化 sample.c"
cmp -s out.c "$RECIPE/expected.c"
chk $? "格式化输出与黄金输出 expected.c 逐字节一致"

########################################################################
say "3. 幂等性（格式化结果稳定）"
cp out.c once.c
"$UNC" -c "$RECIPE/style.cfg" -f once.c -o twice.c > idem.log 2>&1
chk $? "对已格式化输出再次格式化"
cmp -s once.c twice.c
chk $? "二次格式化输出与首次逐字节一致（幂等）"

########################################################################
say "4. stdin 通道与文件通道等价"
"$UNC" -c "$RECIPE/style.cfg" -l C < "$RECIPE/sample.c" > stdin.c 2> stdin.log
chk $? "从 stdin 按 -l C 格式化"
cmp -s stdin.c out.c
chk $? "stdin 通道输出与文件通道逐字节一致"

########################################################################
say "5. 错误路径：配置文件不存在必须非零退出"
"$UNC" -c "$WORK/no-such-config.cfg" -f "$RECIPE/sample.c" -o bad.c \
    > badcfg.log 2>&1
rc=$?
if [ "$rc" -ne 0 ] && [ "$rc" -ne 137 ] && [ "$rc" -ne 141 ]; then
  ok "缺失配置文件时退出码非零 (rc=$rc)"
else
  no "缺失配置文件仍返回 rc=$rc"
fi

########################################################################
say "6. 鸿蒙平台专项：已安装二进制为 AArch64 且带 .codesign 执行段"
UNC_BIN=""
for d in $(printf '%s' "$PATH" | tr ':' ' '); do
  if [ -x "$d/$UNC" ]; then UNC_BIN="$d/$UNC"; break; fi
done
READELF=$(command -v readelf 2>/dev/null || command -v llvm-readelf 2>/dev/null)
if [ -z "$READELF" ] || [ -z "$UNC_BIN" ]; then
  sk "readelf 或已安装 uncrustify 不可得（readelf=${READELF:-none} bin=${UNC_BIN:-none}）"
else
  "$READELF" -h "$UNC_BIN" | grep -q 'AArch64'
  chk $? "已安装 uncrustify 是 AArch64 ELF"
  "$READELF" -S "$UNC_BIN" | grep -q 'codesign'
  chk $? "已安装 uncrustify 带 .codesign 执行段（OHOS 自签名）"
fi

########################################################################
say "7. 鸿蒙平台专项：经 hnp bash 包装在 OHOS 内真实执行"
HNP_BASH=/data/service/hnp/bin/bash
if [ -x "$HNP_BASH" ]; then
  "$HNP_BASH" -c 'uncrustify --version' > hnpbash.log 2>&1
  [ $? -eq 0 ] && grep -q 'Uncrustify-0.79.0' hnpbash.log
  chk $? "hnp bash 包装执行 uncrustify --version 成功"
else
  sk "/data/service/hnp/bin/bash 不存在"
fi

########################################################################
printf '\nRESULT summary: PASS=%d FAIL=%d TOTAL=%d SKIP=%d\n' \
       "$PASS" "$FAIL" "$((PASS + FAIL))" "$SKIP"
if [ "$FAIL" -ne 0 ]; then
  echo "RESULT: FAILED"
  exit 1
fi
echo "RESULT: OK"
exit 0
