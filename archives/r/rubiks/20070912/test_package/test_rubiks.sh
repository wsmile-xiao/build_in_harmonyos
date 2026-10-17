#!/bin/sh
# rubiks 20070912 test_package：只调用已安装进 PATH 的产物（R34/PF3）。
# 每条断言都可证伪：退出码 + 逐字文案；期望值全部取自本机实测的参考输出
# （~/tmp/uc2/z32-rubiks/ev/run-*.out，2026-09-25）。

# 运行产物写到仓库外的独立目录（W4R1-P2-01 整改，实拍依据见 notes.md §5）：
# 本 test_package 被 conan 执行时 cwd 就是本目录，若产物与提交态参考夹具同名同址，
# 一次失败运行就会把真实参考输出覆盖成失败残件 ⇒ 断言退化成「拿失败比失败」。
# 两条独立来源：期望 = 下面写死的逐字串 + 提交态参考夹具 tc-*.txt；实际 = 本轮写到 $OUT 的产物。
OUT="${RUBIKS_TP_OUT:-${TMPDIR:-$HOME/tmp}/rubiks-20070912-test-run}"
mkdir -p "$OUT" || exit 3
echo "TP_PWD=$PWD"
echo "TP_OUT=$OUT"
A=0
F=0
expect_rc() { A=$((A+1)); if [ "$1" = "$2" ]; then echo "ok   [rc] $3 = $1"; else echo "FAIL [rc] $3 got=$1 want=$2"; F=$((F+1)); fi; }
expect_text() { A=$((A+1)); if grep -qF -- "$1" "$2"; then echo "ok   [txt] $2 :: $1"; else echo "FAIL [txt] $2 missing :: $1"; F=$((F+1)); fi; }

A=$((A+1))
MISS=""
for b in cu2 cubex mcube optimal dikcube size222; do
  command -v "$b" >/dev/null 2>&1 || MISS="$MISS $b"
done
if [ -z "$MISS" ]; then echo "ok   [bin] 6 个命令均可从 PATH 解析"; else echo "FAIL [bin] 缺失:$MISS"; F=$((F+1)); fi

timeout 300 mcube random </dev/null >"$OUT/tc-mcube-random.txt" 2>&1
expect_rc "$?" 0 "mcube random"
expect_text "200 cube solved ok." "$OUT/tc-mcube-random.txt"
expect_text "101 version 1.0 (20051216)" "$OUT/tc-mcube-random.txt"

timeout 300 cu2 </dev/null >"$OUT/tc-cu2.txt" 2>&1
expect_rc "$?" 255 "cu2 (无协议输入)"
expect_text "510 ERROR: non-protocol input entered." "$OUT/tc-cu2.txt"

timeout 300 cubex </dev/null >"$OUT/tc-cubex.txt" 2>&1
expect_rc "$?" 255 "cubex (无协议输入)"
expect_text "101 version 1.30.505 by Eric Dietz (root@wrongway.org)" "$OUT/tc-cubex.txt"

timeout 300 size222 -q </dev/null >"$OUT/tc-size222.txt" 2>&1
expect_rc "$?" 0 "size222 -q"
expect_text "1 with  0 turns" "$OUT/tc-size222.txt"
expect_text "6 with  1 turns" "$OUT/tc-size222.txt"
expect_text "27 with  2 turns" "$OUT/tc-size222.txt"
expect_text "312 with  3 turns" "$OUT/tc-size222.txt"

timeout 300 optimal -h </dev/null >"$OUT/tc-optimal.txt" 2>&1
expect_rc "$?" 0 "optimal -h"
expect_text "using quarter turn metric" "$OUT/tc-optimal.txt"

timeout 300 dikcube -p </dev/null >"$OUT/tc-dikcube.txt" 2>&1
expect_rc "$?" 1 "dikcube -p"
expect_text "Initialized = 2187" "$OUT/tc-dikcube.txt"

echo "ASSERTIONS_RUN=$A ASSERTIONS_EXPECT=17 ASSERTIONS_FAILED=$F"
if [ "$F" != 0 ] || [ "$A" != 17 ]; then
  echo "TEST PACKAGE FAILED"
  exit 1
fi
echo "TEST PACKAGE PASSED (17/17)"
