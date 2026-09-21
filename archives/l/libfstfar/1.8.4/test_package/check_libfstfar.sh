#!/bin/sh
# libfstfar 1.8.4 test_package 鸿蒙侧检查（端到端跑本包安装的产物）。
#
# 用法: sh check_libfstfar.sh <libdir> <includedir> <bindir> <workdir>
#
# 每一项检查独立计数并逐条打印 check-ok / CHECK-FAIL，末尾输出机器可读的
# HMBS_HARMONY_SHELL_CHECKS=<执行数> HMBS_HARMONY_SHELL_FAILED=<失败数>。
# 只依赖本包产物 + 包内自带的 far*/fst* 命令行工具，不依赖设备上任何第三方包。
# 调用方（test_package/conanfile.py）用 `env="conanrun"` 运行，故共享库可解析。
#
# 关于安全模式：本脚本是**汇总式**检查——必须跑完全部检查再看总计数，
# 因此刻意**不加 `set -e`**（单项失败由 check() 计数，末尾按 FAILED 决定退出码）。
# 用 `set -u` 保证未定义变量立刻暴露；写成 POSIX sh，由调用方以 `sh <script>` 执行
# （E087：HMDFS 不支持 chmod，脚本文件没有执行位，直接执行会 Error 126）。
set -u

LIBDIR=${1:?libdir}
INCDIR=${2:?includedir}
BINDIR=${3:?bindir}
WORKDIR=${4:?workdir}

CHECKS=0
FAILED=0

check() {
  # check <描述> <命令...>
  desc=$1
  shift
  CHECKS=$((CHECKS + 1))
  if "$@" >/dev/null 2>&1; then
    echo "check-ok: $desc"
  else
    FAILED=$((FAILED + 1))
    echo "CHECK-FAIL: $desc"
  fi
}

check_ok() {
  desc=$1
  CHECKS=$((CHECKS + 1))
  echo "check-ok: $desc"
}

check_bad() {
  desc=$1
  CHECKS=$((CHECKS + 1))
  FAILED=$((FAILED + 1))
  echo "CHECK-FAIL: $desc"
}

# 1) libfstfar 产物随包安装（默认 shared 形态为 libfstfar.so.26，static 形态为 libfstfar.a）
if [ -e "$LIBDIR/libfstfar.a" ] || [ -e "$LIBDIR/libfstfar.so" ] || [ -e "$LIBDIR/libfstfar.dylib" ]; then
  check_ok "libfstfar artifact installed in $LIBDIR"
else
  check_bad "libfstfar artifact installed in $LIBDIR"
fi

# 2) FAR 公共头文件随包安装
check "FAR public headers installed (far.h/stlist.h/sttable.h/far-class.h/farlib.h)" \
  test -f "$INCDIR/fst/extensions/far/far.h" -a \
       -f "$INCDIR/fst/extensions/far/stlist.h" -a \
       -f "$INCDIR/fst/extensions/far/sttable.h" -a \
       -f "$INCDIR/fst/extensions/far/far-class.h" -a \
       -f "$INCDIR/fst/extensions/far/farlib.h"

# 3) 9 个 far* 命令行工具 + 核心 fstcompile/fstprint/fstinfo 随包安装
MISSING_BIN=""
for b in farcompilestrings farconvert farcreate farencode farequal \
         farextract farinfo farisomorphic farprintstrings fstcompile fstprint fstinfo; do
  [ -x "$BINDIR/$b" ] || [ -f "$BINDIR/$b" ] || MISSING_BIN="$MISSING_BIN $b"
done
if [ -z "$MISSING_BIN" ]; then
  check_ok "far* + fst* command-line tools installed in $BINDIR"
else
  check_bad "missing packaged tools:$MISSING_BIN"
fi

rm -rf "$WORKDIR/cli"
mkdir -p "$WORKDIR/cli"
cd "$WORKDIR/cli" || exit 1

# 4) 用本包 fstcompile 把文本 FST 编译成二进制（写出方向，不需要类型注册表）
printf '0 1 1 1 0.25\n1 0.5\n' > in.txt
check "fstcompile converts text FST to binary" \
  "$BINDIR/fstcompile" in.txt in.fst

# 5) 用本包 farcreate 建一个 STList 档案（顺序档案；STListReader::Find 上游直接
#    LOG(FATAL) "Operation not supported"，所以这类档案不能用 --keys 抽取）
check "farcreate --far_type=stlist builds a sequential FST archive" \
  "$BINDIR/farcreate" --far_type=stlist --key_prefix=entry_ in.fst list.far

# 6) 建 STTable 档案并**按 key 读回**：farinfo 不带 --list_fsts 只打聚合统计，
#    带 --list_fsts 才逐条列 key。这一步是「FST 类型注册表是否被保住」的关键判据：
#    静态链接剥离 fst-types.o 时 farinfo 会报 Unknown FST type / # of FSTs 0
#    （见 notes.md 遇到的问题 2）。
rm -f table.far
if "$BINDIR/farcreate" --far_type=sttable --key_prefix=entry_ in.fst table.far > farcreate.out 2>&1 \
   && "$BINDIR/farinfo" table.far > farinfo.out 2>&1 \
   && "$BINDIR/farinfo" --list_fsts table.far > farlist.out 2>&1 \
   && grep -q "entry_in.fst" farlist.out \
   && grep -Eq "^# of FSTs[[:space:]]+1" farinfo.out; then
  check_ok "farcreate --far_type=sttable + farinfo reads key entry_in.fst back (type registry intact)"
else
  check_bad "farcreate --far_type=sttable + farinfo reads key entry_in.fst back (type registry intact)"
  cat farcreate.out farinfo.out farlist.out >&2 2>/dev/null || true
fi

# 7) 用本包 farextract 按 key 抽回条目成独立 FST，并能被 fstinfo 解析
check "farextract --keys extracts the entry back to a valid FST" \
  sh -c "\"$BINDIR/farextract\" --keys=entry_in.fst table.far >/dev/null 2>&1 && \"$BINDIR/fstinfo\" entry_in.fst >/dev/null 2>&1"

# 8) 端到端往返一致：抽回的 FST 打印成文本后与原始文本一致
#    （fstprint 用 TAB 分隔字段、原始文本用空格，先归一化空白再 diff）
check "extracted FST round-trips back to the original text (whitespace-normalized diff)" \
  sh -c "\"$BINDIR/fstprint\" entry_in.fst > printed.txt 2>/dev/null && tr -s ' \t' ' ' < in.txt > in.norm && tr -s ' \t' ' ' < printed.txt > printed.norm && diff -u in.norm printed.norm"

echo "HMBS_HARMONY_SHELL_CHECKS=$CHECKS HMBS_HARMONY_SHELL_FAILED=$FAILED"
if [ "$FAILED" -ne 0 ]; then
  echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"command\":\"check_libfstfar.sh\",\"checks\":$CHECKS,\"failed\":$FAILED}"
  exit 1
fi
echo "PASS libfstfar packaged artifacts and far* CLI round trip"
echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":true,\"command\":\"check_libfstfar.sh\",\"checks\":$CHECKS,\"failed\":0}"
