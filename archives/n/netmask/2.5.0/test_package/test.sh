#!/bin/bash
# test_package/test.sh — netmask 2.5.0 实质测试（R34）：完整复刻上游 v2.5.0 全部 34 个 check
#
# 由 test_package/conanfile.py test() 以 bash 显式执行，NETMASK_BIN 环境变量传入
# 包内 netmask 二进制绝对路径。
#
# 上游测试 = make check（TESTS=./testscript，纯 shell + diff 对比 tests/ 期望文件，
# 实测 34 个 check 全 ok；testscript 中 TAP 头 `echo "1..23"` 为过时计数）。
# 本脚本逐条复刻上游 v2.5.0 testscript 的 34 个 check（编号 1-34 ↔ 上游 testscript
# check 顺序）：对每条用例**真实执行 netmask 二进制**（含 `-f -` 管道 stdin 用例），
# stdout 与本 test_package 携带的 fixtures/（上游 tests/ 34 个期望文件的逐字节拷贝）
# 做 `diff -au`，与上游 `eval $3 | diff -au $2 -` 完全同语义，任一失败即 exit 1
# （R34/PF3 口径：非 print-only 空壳）。
#
# fixtures/ 来源与校验：取自已核实 sha256 的官方 release 资产 netmask-2.5.0.tar.gz
#   （sha256 5975a37f…2f4c73）的 tests/ 目录（34 个文件）；可对照上游
#   https://github.com/tlby/netmask/tree/v2.5.0/tests 逐文件复核。

set -u

NETMASK_BIN="${NETMASK_BIN:-netmask}"

# ---------- preflight（环境健全性检查；不属于上游 34 个 check，不参与计数）----------
if [ ! -x "$NETMASK_BIN" ]; then
    echo "FATAL: netmask binary not found/executable at $NETMASK_BIN"
    exit 1
fi
ver=$("$NETMASK_BIN" -v 2>&1) || true
case "$ver" in
    *2.5.0*) ;;
    *) echo "FATAL: unexpected netmask version output: $ver"; exit 1 ;;
esac
echo "preflight ok: $NETMASK_BIN ($ver)"

TMPD=".netmask-tp.$$"
mkdir -p "$TMPD" || { echo "FATAL: cannot create tmp dir $TMPD"; exit 1; }
trap 'rm -rf "$TMPD"' EXIT INT TERM

PASS=0
FAIL=0

# ---------- 与上游 testscript 同语义的执行器 ----------
# 语义：`eval <cmd> | diff -au fixtures/<fixture> -`，<cmd> 内使用 $netmask 变量。
# （上游 testscript 的 check() 定义为 `i+=1; eval $3 | diff -au "$base$2" -`）
netmask="$NETMASK_BIN"
i=0
check () { # desc fixture cmd
    i=$(expr $i + 1)
    ( cd "$TMPD" && eval "$3" ) > "$TMPD/out"
    if diff -au "fixtures/$2" "$TMPD/out" > "$TMPD/diff" 2>&1; then
        echo "ok $i - $1"
        PASS=$((PASS + 1))
    else
        echo "not ok $i - $1"
        if [ -s "$TMPD/diff" ]; then sed 's/^/    /' "$TMPD/diff"; fi
        FAIL=$((FAIL + 1))
    fi
}

# ============ 34 个用例（顺序与上游 v2.5.0 testscript 一致） ============
check "simple one element" simple             "$netmask 0"
check "simple multi element" simple2          "$netmask 0 2 4 6 8"
check "input formats" inputs                  "$netmask 0 02 0x4 0.0.0.6"
check "simple ranges" range                   "$netmask 100:200"
check "CIDR ranges" range_cidr                "$netmask 12.34.56.78/20"
check "large ranges" range_large              "$netmask 1:0x7ffffffe 0x80000001:0xfffffffe"
check "output format standard" output_std     "$netmask --standard 0 2 4 6 8"
check "output format cidr" output_cidr        "$netmask --cidr 0 2 4 6 8 077777777 0xffffffff"
check "output format cisco" output_cisco      "$netmask --cisco 0 2 4 6 8 077777777 0xffffffff"
check "output format range" output_range      "$netmask --range 0 2 4 6 8 077777777 0xffffffff"
check "output format hex" output_hex          "$netmask --hex 0 2 4 6 8 077777777 0xffffffff"
check "output format octal" output_octal      "$netmask --octal 0 2 4 6 8 077777777 0xffffffff"
check "output format binary" output_binary    "$netmask --binary 0 2 4 6 8 077777777 0xffffffff"
check "subset skipping" subset_skip           "$netmask 345 100:200 105 45 200"
check "subset clean" subset_clean             "$netmask 105 45 200 100:200 345"
check "range joining" range_join              "$netmask 10.1.0.0/16 10.2.0.0/16 10.3.0.0/16 10.4.0.0/16"
check "entire range joining" range_join2      "$netmask 10.0.0.0/16 10.1.0.0/16 10.2.0.0/16 10.3.0.0/16"
check "boundary dottedq 1" bounds_dq1         "$netmask 192.168.0.1/0.0.0.0"
check "boundary dottedq 2" bounds_dq2         "$netmask 192.168.0.1/255.0.0.0"
check "boundary dottedq 3" bounds_dq3         "$netmask 192.168.0.1/255.255.0.0"
check "boundary dottedq 4" bounds_dq4         "$netmask 192.168.0.1/255.255.255.0"
check "boundary dottedq 5" bounds_dq5         "$netmask 192.168.0.1/255.255.255.255"
check "boundary dottedq 6" bounds_dq6         "$netmask 192.168.0.1/0.255.255.255"
check "range adds" range_adds                 "$netmask 10.0.0.1,+5 172.16.29.1:+7"
check "range order" range_order               "$netmask 200:100"
check "range special" range_special           "$netmask 0.0.0.5:+-2"
check "v6 simple" ipv6_simple                 "$netmask ::0 ::2 ::4 ::6 ::8"
check "v6 cisco" v6_cisco                     "$netmask -i 2000::/32"
check "v6 hex" v6_hex                         "$netmask -x 2000::/32"
check "v6 octal" v6_octal                     "$netmask -o 2000::/32"
check "v6 binary" v6_binary                   "$netmask -b 2000::/32"
check "file input" file_input                 "echo 1.2.3.4 | $netmask -f -"
check "coverage 1" coverage1                  "$netmask -r 12 12/24 12/16 2000::/64 2001::/::ffff"
# IPv4-mapped 区边界：确保非 CIDR range 进出该区行为不变
check "v4 edge" v4_edge                       "$netmask ::fffe:ffff:ffff,+1 255.255.255.255:+1"

echo "==== test_package summary: UPSTREAM_CHECKS=34 PASS=$PASS FAIL=$FAIL ===="
if [ "$FAIL" -ne 0 ]; then exit 1; fi
exit 0
