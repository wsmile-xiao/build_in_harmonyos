#!/bin/bash
# test_package/test.sh — netmask 2.4.4 实质测试（R34）：完整复刻上游 v2.4.4 全部 26 个 check
#
# 由 test_package/conanfile.py test() 以 bash 显式执行，NETMASK_BIN 环境变量传入
# 包内 netmask 二进制绝对路径。
#
# 上游测试 = make check（TESTS=./testscript，纯 shell + diff 对比 tests/ 期望文件，
# 实测 26 个 check 全 ok；testscript 中 TAP 头 `echo "1..23"` 为过时计数）。
# 本脚本把上游 26 个 check 逐条复刻（编号 1-26 ↔ 上游 testscript check 1-26）：
#   对每条用例**真实执行 netmask 二进制**，将 stdout 与本 test_package 携带的
#   fixtures/（上游 v2.4.4 tests/ 26 个期望文件的逐字节拷贝）做 `diff -au`，
#   与上游 testscript `eval $3 | diff -au $2 -` 完全同语义，任一失败即 exit 1
#   （R34/PF3 口径：非 print-only 空壳）。
#
# fixtures/ 来源与校验：取自已核实 sha256 的 Debian orig tarball
#   netmask_2.4.4.orig.tar.gz 的 tests/ 目录（26 个文件）；可对照上游
#   https://github.com/tlby/netmask/tree/v2.4.4/tests 逐文件复核。

set -u

NETMASK_BIN="${NETMASK_BIN:-netmask}"

# ---------- preflight（环境健全性检查；不属于上游 26 个 check，不参与计数）----------
if [ ! -x "$NETMASK_BIN" ]; then
    echo "FATAL: netmask binary not found/executable at $NETMASK_BIN"
    exit 1
fi
ver=$("$NETMASK_BIN" -v 2>&1) || true
case "$ver" in
    *2.4.4*) ;;
    *) echo "FATAL: unexpected netmask version output: $ver"; exit 1 ;;
esac
echo "preflight ok: $NETMASK_BIN ($ver)"

TMPD=".netmask-tp.$$"
mkdir -p "$TMPD" || { echo "FATAL: cannot create tmp dir $TMPD"; exit 1; }
trap 'rm -rf "$TMPD"' EXIT INT TERM

PASS=0
FAIL=0

# run_check <no> <desc> <fixture> <args...>：执行 netmask，与 fixtures/<fixture> diff
run_check() { # no desc fixture args...
    no="$1"; desc="$2"; fix="$3"; shift 3
    "$NETMASK_BIN" "$@" > "$TMPD/out" 2>&1
    if diff -au "fixtures/$fix" "$TMPD/out" > "$TMPD/diff" 2>&1; then
        echo "ok $no - $desc"
        PASS=$((PASS + 1))
    else
        echo "not ok $no - $desc"
        if [ -s "$TMPD/diff" ]; then sed 's/^/    /' "$TMPD/diff"; fi
        FAIL=$((FAIL + 1))
    fi
}

# ============ 26 个用例（与上游 testscript check 一一对应） ============

# #1 simple one element   netmask 0
run_check 1  "simple one element"      simple        0
# #2 simple multi element  netmask 0 2 4 6 8
run_check 2  "simple multi element"    simple2       0 2 4 6 8
# #3 input formats        netmask 0 02 0x4 0.0.0.6
run_check 3  "input formats"           inputs        0 02 0x4 0.0.0.6
# #4 simple ranges        netmask 100:200
run_check 4  "simple ranges"           range         100:200
# #5 CIDR ranges          netmask 12.34.56.78/20
run_check 5  "CIDR ranges"             range_cidr    12.34.56.78/20
# #6 large ranges         netmask 1:0x7ffffffe 0x80000001:0xfffffffe
run_check 6  "large ranges"            range_large   1:0x7ffffffe 0x80000001:0xfffffffe
# #7 output format standard  netmask --standard 0 2 4 6 8
run_check 7  "output format standard"  output_std    --standard 0 2 4 6 8
# #8 output format cidr   netmask --cidr 0 2 4 6 8 077777777 0xffffffff
run_check 8  "output format cidr"      output_cidr   --cidr 0 2 4 6 8 077777777 0xffffffff
# #9 output format cisco  netmask --cisco 0 2 4 6 8 077777777 0xffffffff
run_check 9  "output format cisco"     output_cisco  --cisco 0 2 4 6 8 077777777 0xffffffff
# #10 output format range netmask --range 0 2 4 6 8 077777777 0xffffffff
run_check 10 "output format range"     output_range  --range 0 2 4 6 8 077777777 0xffffffff
# #11 output format hex   netmask --hex 0 2 4 6 8 077777777 0xffffffff
run_check 11 "output format hex"       output_hex    --hex 0 2 4 6 8 077777777 0xffffffff
# #12 output format octal netmask --octal 0 2 4 6 8 077777777 0xffffffff
run_check 12 "output format octal"     output_octal  --octal 0 2 4 6 8 077777777 0xffffffff
# #13 output format binary netmask --binary 0 2 4 6 8 077777777 0xffffffff
run_check 13 "output format binary"    output_binary --binary 0 2 4 6 8 077777777 0xffffffff
# #14 subset skipping     netmask 345 100:200 105 45 200
run_check 14 "subset skipping"         subset_skip   345 100:200 105 45 200
# #15 subset clean        netmask 105 45 200 100:200 345
run_check 15 "subset clean"            subset_clean  105 45 200 100:200 345
# #16 range joining       netmask 10.1.0.0/16 10.2.0.0/16 10.3.0.0/16 10.4.0.0/16
run_check 16 "range joining"           range_join    10.1.0.0/16 10.2.0.0/16 10.3.0.0/16 10.4.0.0/16
# #17 entire range joining netmask 10.0.0.0/16 10.1.0.0/16 10.2.0.0/16 10.3.0.0/16
run_check 17 "entire range joining"    range_join2   10.0.0.0/16 10.1.0.0/16 10.2.0.0/16 10.3.0.0/16
# #18 boundary dottedq 1  netmask 192.168.0.1/0.0.0.0
run_check 18 "boundary dottedq 1"      bounds_dq1    192.168.0.1/0.0.0.0
# #19 boundary dottedq 2  netmask 192.168.0.1/255.0.0.0
run_check 19 "boundary dottedq 2"      bounds_dq2    192.168.0.1/255.0.0.0
# #20 boundary dottedq 3  netmask 192.168.0.1/255.255.0.0
run_check 20 "boundary dottedq 3"      bounds_dq3    192.168.0.1/255.255.0.0
# #21 boundary dottedq 4  netmask 192.168.0.1/255.255.255.0
run_check 21 "boundary dottedq 4"      bounds_dq4    192.168.0.1/255.255.255.0
# #22 boundary dottedq 5  netmask 192.168.0.1/255.255.255.255
run_check 22 "boundary dottedq 5"      bounds_dq5    192.168.0.1/255.255.255.255
# #23 boundary dottedq 6  netmask 192.168.0.1/0.255.255.255
run_check 23 "boundary dottedq 6"      bounds_dq6    192.168.0.1/0.255.255.255
# #24 range adds          netmask 10.0.0.1,+5 172.16.29.1:+7
run_check 24 "range adds"              range_adds    10.0.0.1,+5 172.16.29.1:+7
# #25 range order         netmask 200:100
run_check 25 "range order"             range_order   200:100
# #26 range special       netmask 0.0.0.5:+-2
run_check 26 "range special"           range_special 0.0.0.5:+-2

echo "==== test_package summary: UPSTREAM_CHECKS=26 PASS=$PASS FAIL=$FAIL ===="
if [ "$FAIL" -ne 0 ]; then exit 1; fi
exit 0
