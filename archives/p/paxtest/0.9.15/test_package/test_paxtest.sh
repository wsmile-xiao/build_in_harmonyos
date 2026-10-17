#!/bin/sh
# test_paxtest.sh — consumer tests for paxtest/0.9.15 (CI L1).
#
# Usage: sh test_paxtest.sh <suite-dir> <work-dir>
#
# 通过口径（安全探测类套件，无传统断言框架）：包结构完整；exec/mprotect/writetext
# 探测项真实运行（rc=0）且结果不是 Vulnerable；地址类 helper 输出可解析；快速随机化
# 项给出质量位数；驱动对无参数调用打印 usage 并拒绝（负向对照）。
# 说明：完整随机化项（randbody COUNT=1500 × 13）耗时较长，不在本测试内运行；
#      其真机结果见归档 reports/device-kiddie*.log 与 reports/test-report.md。
set -u

SUITE="$1"
WORK="$2"
CHECKS=0
FAILS=0

check() {
    desc="$1"
    shift
    CHECKS=$((CHECKS + 1))
    if "$@"; then
        echo "ok $CHECKS - $desc"
    else
        echo "not ok $CHECKS - $desc"
        FAILS=$((FAILS + 1))
    fi
}

cd "$SUITE" || exit 1
export LD_LIBRARY_PATH="$SUITE${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export PAXTEST_MODE=0

# 1) 包结构
check "driver paxtest is shipped" test -x "$SUITE/paxtest"
check "chpax tool is shipped" test -x "$SUITE/chpax"
check "shlibtest.so is shipped" test -f "$SUITE/shlibtest.so"
check "upstream README is shipped" test -f "$SUITE/README"

n=0
for t in anonmap execbss execdata execheap execstack shlibbss shlibdata \
         mprotanon mprotbss mprotdata mprotheap mprotstack mprotshbss mprotshdata writetext \
         randamap randheap1 randheap2 randmain1 randmain2 randshlib randvdso randstack1 randstack2 \
         randarg1 randarg2 randshlibdelta1 randshlibdelta2 randexhaust1 randexhaust2 \
         rettofunc1 rettofunc2 rettofunc1x rettofunc2x; do
    [ -x "$SUITE/$t" ] && n=$((n + 1))
done
check "all 34 test programs are executable" test "$n" -eq 34

# 2) 攻击探测执行：rc=0 且结果不得为 Vulnerable
probe() {
    p="$1"
    rx="$2"
    "./$p" > "$WORK/$p.out" 2>&1
    rc=$?
    check "$p exits 0" test "$rc" -eq 0
    check "$p result matches" grep -Eq "$rx" "$WORK/$p.out"
    echo "# $p: $(tr '\n' ' ' < "$WORK/$p.out")"
}

probe execstack  '^Executable stack +: (Killed|Ok)$'
probe anonmap    '^Executable anonymous mapping +: (Killed|Ok)$'
probe mprotstack '^Executable stack \(mprotect\) +: (Killed|Ok)$'
probe writetext  '^Writable text segments +: (Killed|Ok)$'

# 3) 地址 helper：输出可解析的地址
"./getamap" > "$WORK/getamap.out" 2>&1
check "getamap exits 0" test "$?" -eq 0
check "getamap prints an address" grep -Eq '^0x?[0-9a-f]+' "$WORK/getamap.out"
echo "# getamap: $(cat "$WORK/getamap.out")"

"./getstack1" > "$WORK/getstack1.out" 2>&1
check "getstack1 exits 0" test "$?" -eq 0
check "getstack1 prints an address" grep -Eq '^0x?[0-9a-f]+' "$WORK/getstack1.out"
echo "# getstack1: $(cat "$WORK/getstack1.out")"

# 4) 快速随机化项（fastrandbody COUNT=25；getexhaust1 在 64 位上为单次 mmap）
"./randexhaust1" > "$WORK/randexhaust1.out" 2>&1
check "randexhaust1 exits 0" test "$?" -eq 0
check "randexhaust1 reports randomization quality" \
    grep -Eq '^Randomization under memory exhaustion.*: ([0-9]+ bits \(guessed\)|No randomization)$' "$WORK/randexhaust1.out"
echo "# randexhaust1: $(cat "$WORK/randexhaust1.out")"

# 5) 负向对照：无模式参数必须拒绝并打印 usage
"./paxtest" > "$WORK/paxtest-usage.out" 2>&1
NEG=$?
check "driver rejects missing mode (negative control)" test "$NEG" -ne 0
check "driver prints usage" grep -q "usage: paxtest" "$WORK/paxtest-usage.out"

echo "1..$CHECKS"
if [ "$FAILS" -ne 0 ]; then
    echo "# FAILED $FAILS/$CHECKS checks"
    exit 1
fi
echo "# all $CHECKS checks passed"
exit 0
