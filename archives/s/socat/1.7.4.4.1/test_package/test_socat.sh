#!/bin/bash
# test_package 功能测试 — socat 1.7.4.4.1（基于上游 1.7.4.4 的适配轮次）
#
# 消费者视角验证：实际执行交付产物并断言运行时行为。
# 断言（每项成功 +1 check）：
#   1. socat -V 真实运行并输出版本号
#   2. socat -h 帮助可用
#   3. 单向中继：socat -u exec:... - 把子进程输出转发到 stdout
#   4. TCP 中继：起监听端 + 客户端，验证 socket 转发（socat 的核心能力）
#   5. filan 可执行
#   6. procan 可执行
#
# 不使用 /tmp（OHOS 上只读 erofs），临时文件放当前工作目录。

set -u

CHECKS=0
FAILURES=0

ok()  { CHECKS=$((CHECKS + 1)); echo "  [ok]   $1"; }
bad() { CHECKS=$((CHECKS + 1)); FAILURES=$((FAILURES + 1)); echo "  [FAIL] $1"; }

VERSION_EXPECT="1.7.4.4"
PORT="${SOCAT_TEST_PORT:-23456}"
SRV_PID=""
WORKDIR="./socat-test-$$"

cleanup() {
    [ -n "$SRV_PID" ] && kill "$SRV_PID" 2>/dev/null
    sleep 1
    [ -n "$SRV_PID" ] && kill -9 "$SRV_PID" 2>/dev/null
    [ -n "$WORKDIR" ] && rm -rf "$WORKDIR" 2>/dev/null
}
trap cleanup EXIT

mkdir -p "$WORKDIR" 2>/dev/null

echo "== socat test_package：验证交付产物（socat=$(command -v socat)）=="

# ── 1. socat -V ───────────────────────────────────────────────────────
out=$(socat -V 2>&1)
if echo "$out" | grep -q "socat version ${VERSION_EXPECT}"; then
    ok "socat -V 输出包含 'socat version ${VERSION_EXPECT}'"
else
    bad "socat -V 输出异常：$(echo "$out" | head -2 | tr '\n' ' ')"
fi

# ── 2. socat -h ───────────────────────────────────────────────────────
if socat -h > /dev/null 2>&1 || socat -h 2>&1 | grep -qi "usage"; then
    ok "socat -h 可用"
else
    bad "socat -h 失败"
fi

# ── 3. 单向中继（exec → stdout）───────────────────────────────────────
out=$(socat -u "exec:echo SOCAT_RELAY_OK" - 2>&1)
if echo "$out" | grep -q "SOCAT_RELAY_OK"; then
    ok "单向中继成功（exec:echo → stdout）"
else
    bad "单向中继失败：$(echo "$out" | head -2 | tr '\n' ' ')"
fi

# ── 4. TCP 中继（核心能力：socket 转发）──────────────────────────────
# 监听端：把收到的内容写入文件；客户端：发送字符串后关闭。
# 注意：不使用 `/dev/tcp` 做就绪探测（本环境下不可靠，实测连续探测均失败，
# 但实际转发是成功的），改为「轮询重试发送 + 等待内容到达」，避免竞态假失败。
socat -u "TCP-LISTEN:${PORT},reuseaddr" "CREATE:$WORKDIR/received.txt" \
    > "$WORKDIR/srv.log" 2>&1 &
SRV_PID=$!
MARKER="SOCAT_TCP_RELAY_OK"
relay_ok=0
for _ in 1 2 3 4 5 6 7 8 9 10; do
    printf '%s\n' "$MARKER" | socat -u - "TCP:127.0.0.1:${PORT}" 2>/dev/null || true
    sleep 1
    if grep -q "$MARKER" "$WORKDIR/received.txt" 2>/dev/null; then
        relay_ok=1
        break
    fi
done
if [ "$relay_ok" = "1" ]; then
    ok "TCP 中继成功（客户端 → 监听端，内容已到达）"
else
    bad "TCP 中继失败：监听端未收到内容（srv.log: $(head -2 "$WORKDIR/srv.log" 2>/dev/null | tr '\n' ' '))"
fi
if [ -n "$SRV_PID" ]; then
    kill "$SRV_PID" 2>/dev/null || true
    sleep 1
    kill -9 "$SRV_PID" 2>/dev/null || true
    SRV_PID=""
fi

# ── 5. filan ──────────────────────────────────────────────────────────
if filan -V 2>&1 | grep -q "${VERSION_EXPECT}" || filan -h > /dev/null 2>&1; then
    ok "filan 可执行"
else
    bad "filan 执行失败"
fi

# ── 6. procan ─────────────────────────────────────────────────────────
if procan -V 2>&1 | grep -q "${VERSION_EXPECT}" || procan -h > /dev/null 2>&1; then
    ok "procan 可执行"
else
    bad "procan 执行失败"
fi

echo
if [ "$FAILURES" -eq 0 ]; then
    echo "RESULT: PASS (${CHECKS} checks, 0 failures)"
    exit 0
else
    echo "RESULT: FAIL (${CHECKS} checks, ${FAILURES} failures)"
    exit 1
fi
