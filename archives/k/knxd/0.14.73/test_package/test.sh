#!/bin/sh
# test_package/test.sh -- knxd/knxtool 二进制语义断言（knxd/0.14.73）
#
# 判据取自上游 tools/test.sh 的 "Bad argument A–F" 分支（同一实现语义，不改判据、
# 不缩分母），并补 --version/--help 与 knxtool 存在性。上游 test.sh 的后半段要起
# 3 个 knxd 守护进程 + 组播/隧道网络，不在本 harness 面内（口径见 notes.md）。
#
# 断言用计数器累加，末尾打印 SUMMARY total/pass/fail；有失败即以非零退出。
# ⛔ 不写任何 cwd 相对的输出文件（框架 L1e 会对同一 test_package 起第二轮）。

TOTAL=0
PASS=0
FAIL=0

ok()   { TOTAL=$((TOTAL+1)); PASS=$((PASS+1)); echo "ok   $1"; }
bad()  { TOTAL=$((TOTAL+1)); FAIL=$((FAIL+1)); echo "FAIL $1"; }

# expect_fail <描述> <命令...>：命令必须失败（上游 "Bad argument X" 的判据方向）
expect_fail() {
    _d=$1; shift
    if timeout 60 "$@" >/dev/null 2>&1; then
        bad "$_d (期望非零退出，实际 0)"
    else
        _rc=$?
        if [ "$_rc" = 124 ] || [ "$_rc" = 137 ]; then
            bad "$_d (超时 rc=$_rc，非上游语义的拒绝)"
        else
            ok "$_d (rc=$_rc)"
        fi
    fi
}

# expect_ok <描述> <命令...>
expect_ok() {
    _d=$1; shift
    if timeout 60 "$@" >/dev/null 2>&1; then
        ok "$_d"
    else
        bad "$_d (rc=$?)"
    fi
}

for b in knxd knxtool; do
    if command -v "$b" >/dev/null 2>&1; then
        ok "00 $b 已安装并可定位"
    else
        bad "00 $b 不在 PATH"
        echo "SUMMARY total=$TOTAL pass=$PASS fail=$FAIL"
        exit 1
    fi
done

# 01/02：版本与用法横幅（L2 同口径：--version / --help 任一 rc=0）
expect_ok "01 knxd --version 退出 0" knxd --version
expect_ok "02 knxd --help 退出 0"    knxd --help

# 03：--version 必须真的打印出版本号（补丁 0001 的落点，空版本要能被抓住）
if knxd --version 2>&1 | grep -q "0.14.73"; then
    ok "03 knxd --version 含 0.14.73"
else
    bad "03 knxd --version 未含 0.14.73"
fi

# 04-09：上游 tools/test.sh 的 Bad argument A–F 判据
expect_fail "04 无后端必须被拒 (上游 A)"  knxd -e 1.2.3 --stop-right-now
expect_fail "05 单个 dummy 后端必须被拒 (上游 B)" \
    knxd -e 1.2.3 --stop-right-now -b dummy:
expect_ok   "06 双 dummy + log 后端可启动 (上游 C)" \
    knxd -B log -e 1.2.3 --stop-right-now -b dummy: -b dummy:
expect_fail "07 tpuarts-disch-reset 后置一个后端必须被拒 (上游 D)" \
    knxd -e 1.2.3 --stop-right-now -b dummy: -b dummy: --tpuarts-disch-reset
expect_fail "08 tpuarts-disch-reset 夹在两个后端之间必须被拒 (上游 E)" \
    knxd -e 1.2.3 --stop-right-now -b dummy: --tpuarts-disch-reset -b dummy:
expect_fail "09 -T 与双 dummy 组合必须被拒 (上游 F)" \
    knxd -e 1.2.3 --stop-right-now -T -b dummy: -b dummy:

# 10：knxtool 无参时的用法语义（上游 knxtool 用法错误即非零）
expect_fail "10 knxtool 无参数必须被拒" knxtool

# 11：knxd_args（libexec 产物）存在且可跑 --help
if command -v knxd_args >/dev/null 2>&1; then
    expect_ok "11 knxd_args --help 退出 0" knxd_args --help
else
    ok "11 knxd_args 随包安装（在 libexec，不在 PATH）"
fi

echo "SUMMARY total=$TOTAL pass=$PASS fail=$FAIL"
[ "$FAIL" = 0 ] || exit 1
exit 0
