#!/bin/sh
# test_package/test_trurl.sh — trurl 0.16.1 行为契约测试（离线、确定性，无网络）
#
# R34：真实执行被测包安装出来的 bin/trurl 并断言其真实输出，
# 不是 print-only / pass-only 空壳。所有断言均为精确非空字符串
# 比较（空文件比空文件的假绿在此必然失败）。
#
# 用法: sh test_trurl.sh <trurl 可执行文件路径>
# 退出码 0 = 全部检查通过；非 0 = 有检查失败。
set -u

TRURL="${1:?usage: test_trurl.sh <path-to-trurl>}"

CHECKED=0
PASSED=0
FAILED=0

ok() {
    CHECKED=$((CHECKED + 1))
    PASSED=$((PASSED + 1))
    echo "[PASS] $1"
}

no() {
    CHECKED=$((CHECKED + 1))
    FAILED=$((FAILED + 1))
    echo "[FAIL] $1"
    echo "------- actual output -------"
    printf '%s\n' "$2"
    echo "-----------------------------"
}

# T1: --version 可执行且版本正确（证明二进制可运行 + 版本宏正确）
OUT=$("$TRURL" --version 2>&1)
case "$OUT" in
    *"trurl version 0.16.1"*)
        ok "T1 --version => trurl version 0.16.1"
        ;;
    *)
        no "T1 --version 应包含 'trurl version 0.16.1'" "$OUT"
        ;;
esac

# T2: --help 输出选项表（证明帮助文本被编进二进制）
OUT=$("$TRURL" --help 2>&1)
case "$OUT" in
    *"--url"*)
        case "$OUT" in
            *"--get"*)
                ok "T2 --help => 含 --url/--get"
                ;;
            *)
                no "T2 --help 应包含 --url 与 --get" "$OUT"
                ;;
        esac
        ;;
    *)
        no "T2 --help 应包含 --url 与 --get" "$OUT"
        ;;
esac

# T3: 抽取 path 组件（README 官方示例，精确非空比较）
OUT=$("$TRURL" --url https://curl.se/we/are.html --get '{path}' 2>&1)
if [ "$OUT" = "/we/are.html" ]; then
    ok "T3 get path => /we/are.html"
else
    no "T3 get path 应为 '/we/are.html'" "$OUT"
fi

# T4: 抽取默认端口（scheme 隐含端口推导，精确非空比较）
OUT=$("$TRURL" --url https://curl.se/we/are.html --get '{default:port}' 2>&1)
if [ "$OUT" = "443" ]; then
    ok "T4 get default:port => 443"
else
    no "T4 get default:port 应为 '443'" "$OUT"
fi

# T5: 改写 host（README 官方示例，精确非空比较）
OUT=$("$TRURL" --url https://curl.se --set host=example.com 2>&1)
if [ "$OUT" = "https://example.com/" ]; then
    ok "T5 set host => https://example.com/"
else
    no "T5 set host 应为 'https://example.com/'" "$OUT"
fi

# T6: 多组件组合抽取（含显式端口/path/query，精确非空比较）
OUT=$("$TRURL" --url 'https://example.com:8080/a/b?x=1' --get '{scheme}://{host}:{port}{path}?{query}' 2>&1)
if [ "$OUT" = "https://example.com:8080/a/b?x=1" ]; then
    ok "T6 get scheme/host/port/path/query 组合"
else
    no "T6 组合抽取应为 'https://example.com:8080/a/b?x=1'" "$OUT"
fi

echo "RESULT: ${PASSED} passed, ${FAILED} failed"
[ "$FAILED" -eq 0 ] || exit 1
exit 0
