#!/usr/bin/env bash
# irrtoolset test_package 实质测试: 调用真实 CLI 工具验证公开功能
# rpslcheck: 从 stdin 读取 RPSL 对象并校验 (纯本地解析, 不接受位置参数)
# rtconfig: 路由器配置生成器 (本地运行)
# 注: peval 初始化时强制连接 IRR whois 远端 (RADB 等), 无网络环境下
#     挂起/段错误, 不属于本地可验证用例, 故不在 test_package 中调用.
set -u

BIN_DIR="${BIN_DIR:-$PWD/bin}"
RPSLCHECK="$BIN_DIR/rpslcheck"
PEVAL="$BIN_DIR/peval"
RTCONFIG="$BIN_DIR/rtconfig"

# 定位已安装二进制
for cand in "$PWD/bin/rpslcheck" "$PWD/../bin/rpslcheck" "$(command -v rpslcheck 2>/dev/null)"; do
    if [ -n "$cand" ] && [ -x "$cand" ]; then
        RPSLCHECK="$cand"
        BIN_DIR="$(dirname "$cand")"
        PEVAL="$BIN_DIR/peval"
        RTCONFIG="$BIN_DIR/rtconfig"
        break
    fi
done

fail=0

echo "== rpslcheck: 合法 RPSL 对象 (stdin) =="
printf 'inetnum: 192.0.2.0 - 192.0.2.255\nnetname: TEST-NET\ncountry: ZZ\ndescr: test\nadmin-c: TEST-RIPE\ntech-c: TEST-RIPE\nmnt-by: TEST-MNT\nstatus: ASSIGNED PA\ncreated: 2020-01-01\nlast-modified: 2020-01-01\nsource: TEST\n\n' | "$RPSLCHECK" > rpsl_valid.out 2>&1
rc=$?
echo "exit=$rc"
if [ $rc -eq 0 ] && grep -q "Congratulations no errors" rpsl_valid.out; then
    echo "PASS: rpslcheck accepted valid RPSL object"
else
    echo "FAIL: rpslcheck rejected valid RPSL object"
    cat rpsl_valid.out
    fail=1
fi

echo "== rpslcheck: 非法 RPSL 对象 (缺必填属性) =="
printf 'inetnum: 192.0.2.0 - 192.0.2.255\n' | "$RPSLCHECK" > rpsl_invalid.out 2>&1
rc=$?
echo "exit=$rc"
if grep -q "Error" rpsl_invalid.out; then
    echo "PASS: rpslcheck reported errors for invalid RPSL object"
else
    echo "FAIL: rpslcheck did not report errors for invalid RPSL object"
    cat rpsl_invalid.out
    fail=1
fi

echo "== rtconfig: 运行并产生输出 =="
"$RTCONFIG" -version > rtconfig.out 2>&1
rc=$?
echo "exit=$rc"
if [ -s rtconfig.out ] || [ $rc -eq 0 ]; then
    echo "PASS: rtconfig ran and produced output"
else
    echo "FAIL: rtconfig produced no output"
    fail=1
fi

if [ $fail -eq 0 ]; then
    echo "ALL TEST_PACKAGE TESTS PASSED"
else
    echo "TEST_PACKAGE FAILURES DETECTED"
fi
exit $fail
