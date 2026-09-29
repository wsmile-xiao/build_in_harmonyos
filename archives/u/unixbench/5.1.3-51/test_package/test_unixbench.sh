#!/bin/sh
# test_unixbench.sh — consumer tests for unixbench/5.1.3-51 (CI L1).
#
# Usage: sh test_unixbench.sh <suite-dir> <work-dir>
#
# 通过口径（基准类无传统断言）：每个选中用例产出有效分数（无 err/0 分）
# 且套件退出码为 0。真实执行已安装的预编译基准程序（不依赖编译器）。
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

# 1) 包结构：驱动脚本、Makefile、基线索引
check "driver Run is shipped" test -f "$SUITE/Run"
check "upstream Makefile is shipped" test -f "$SUITE/Makefile"
check "index baseline is shipped" test -f "$SUITE/pgms/index.base"

# 2) 18 个预编译基准程序全部存在且可执行
missing=""
for p in arithoh register short int long float double hanoi syscall context1 \
         pipe spawn execl dhry2 dhry2reg looper fstime whetstone-double; do
    if [ ! -x "$SUITE/pgms/$p" ]; then
        missing="$missing $p"
    fi
done
check "18 prebuilt benchmark programs are executable" test -z "$missing"

# 3) 上游测试数据
check "upstream test data files are shipped" test -f "$SUITE/testdir/large.txt" -a \
    -f "$SUITE/testdir/sort.src" -a -f "$SUITE/testdir/dc.dat" -a -f "$SUITE/testdir/cctest.c"

# 4) 复制到可写目录（保留时间戳，避免触发 make 重建；详见 README.md）
if ! cp -a "$SUITE" "$WORK/suite"; then
    cp -R -p "$SUITE" "$WORK/suite" || exit 1
fi
cd "$WORK/suite" || exit 1

# 5) 实跑 5 项基准（-i 1 缩减迭代；真实执行，非空壳）
#    arithoh 是算术族回归项：修复前 clang -O2 下该族输出 COUNT|0，Run 会以
#    "Can't take log of 0" 中止（rc=25），此用例可捕获该回归。
perl Run -i 1 -q dhry2reg arithoh syscall pipe context1 > run-subset.out 2> run-subset.err
RC=$?
check "benchmark subset exits 0" test "$RC" -eq 0

REPORT=""
for f in results/*; do
    case "$f" in
        *.html|*.log|*.keep) ;;
        results/\*) ;;
        *) REPORT="$f" ;;
    esac
done
check "run report was generated" test -n "$REPORT" -a -f "$REPORT"

if [ -n "$REPORT" ] && [ -f "$REPORT" ]; then
    check "report contains System Benchmarks Index Score" \
        grep -q "System Benchmarks Index Score" "$REPORT"
    check "report contains Dhrystone result" \
        grep -q "Dhrystone 2 using register variables" "$REPORT"
    check "report contains System Call Overhead result" \
        grep -q "System Call Overhead" "$REPORT"
    check "report contains Pipe Throughput result" \
        grep -q "Pipe Throughput" "$REPORT"
    check "report contains Pipe-based Context Switching result" \
        grep -q "Pipe-based Context Switching" "$REPORT"

    SCORE=$(awk '/Dhrystone 2 using register variables/ {v=$(NF-1)} END {print v}' "$REPORT")
    check "Dhrystone score is a positive number (${SCORE:-empty})" \
        awk -v v="${SCORE:-0}" 'BEGIN { exit !(v + 0 > 0) }'

    check "report contains Arithoh result" grep -q -E "^Arithoh " "$REPORT"
    ARITH_SCORE=$(awk '/^Arithoh/ {print $2; exit}' "$REPORT")
    check "Arithoh score is a positive number (${ARITH_SCORE:-empty})" \
        awk -v v="${ARITH_SCORE:-0}" 'BEGIN { exit !(v + 0 > 0) }'

    # OHOS 平台签名：系统信息采集真实反映 HarmonyOS 内核
    check "system info reports the HarmonyOS kernel (HongMeng Kernel)" \
        grep -q "HongMeng Kernel" "$REPORT"
    check "report states the CPUs-in-system line" \
        grep -q -E "[0-9]+ CPUs? in system" "$REPORT"
    echo "# info: $(grep -E "[0-9]+ CPUs? in system" "$REPORT" | head -1)"
fi

# 6) 负向对照：未知用例必须被拒绝
perl Run -i 1 -q __no_such_test__ > /dev/null 2>&1
NEG=$?
check "unknown test name is rejected (negative control)" test "$NEG" -ne 0

echo "1..$CHECKS"
if [ "$FAILS" -ne 0 ]; then
    echo "# FAILED $FAILS/$CHECKS checks"
    exit 1
fi
echo "# all $CHECKS checks passed"
exit 0
