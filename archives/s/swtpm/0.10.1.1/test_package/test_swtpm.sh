#!/bin/bash
# test_package 功能测试 — swtpm 0.10.1
#
# 消费者视角验证：模拟 gnupg tests/tpm2dtests/start_sw_tpm.sh 的用法
#   ${SWTPM} socket --tpm2 --daemon --pid file=swtpm.pid \
#            --server type=tcp,port=2321 --ctrl type=tcp,port=2322 \
#            --flags not-need-init,startup-clear --tpmstate dir=$(pwd)
#
# 断言（每项成功 +1 check）：
#   1-3. 三个核心工具 --version 真实运行且输出版本号
#   4.   swtpm socket --help 可用（gnupg 消费的确切子命令）
#   5.   模拟器能在 TCP 上拉起（进程存活 + pid 文件写入）
#   6.   控制通道端口可建立 TCP 连接（证明真的在服务）
#   7.   模拟器能正常停止并清理状态
#
# 不使用 /tmp（OHOS 上只读 erofs），状态目录取当前工作目录下的子目录。

set -u

CHECKS=0
FAILURES=0

ok()   { CHECKS=$((CHECKS + 1)); echo "  [ok]   $1"; }
bad()  { CHECKS=$((CHECKS + 1)); FAILURES=$((FAILURES + 1)); echo "  [FAIL] $1"; }

VERSION_EXPECT="0.10.1"
STATE_DIR="./swtpm-state-$$"
CTRL_PORT="${SWTPM_TEST_CTRL_PORT:-23222}"
SRV_PORT="${SWTPM_TEST_SRV_PORT:-23221}"
SWTPM_PID=""

cleanup() {
    if [ -n "$SWTPM_PID" ] && kill -0 "$SWTPM_PID" 2>/dev/null; then
        kill "$SWTPM_PID" 2>/dev/null || true
        sleep 1
        kill -9 "$SWTPM_PID" 2>/dev/null || true
    fi
    rm -rf "$STATE_DIR" 2>/dev/null || true
}
trap cleanup EXIT

echo "== swtpm test_package：验证交付产物（swtpm=$(command -v swtpm)）=="

# ── 1. swtpm --version ────────────────────────────────────────────────
out=$(swtpm --version 2>&1)
if echo "$out" | grep -q "TPM emulator version ${VERSION_EXPECT}"; then
    ok "swtpm --version 输出包含 'TPM emulator version ${VERSION_EXPECT}'"
else
    bad "swtpm --version 输出异常：${out}"
fi

# ── 2. swtpm_setup --version ──────────────────────────────────────────
out=$(swtpm_setup --version 2>&1)
if echo "$out" | grep -q "${VERSION_EXPECT}"; then
    ok "swtpm_setup --version 输出版本号"
else
    bad "swtpm_setup --version 输出异常：${out}"
fi

# ── 3. swtpm_ioctl --version ──────────────────────────────────────────
out=$(swtpm_ioctl --version 2>&1)
if echo "$out" | grep -q "${VERSION_EXPECT}"; then
    ok "swtpm_ioctl --version 输出版本号"
else
    bad "swtpm_ioctl --version 输出异常：${out}"
fi

# ── 4. swtpm socket --help（gnupg start_sw_tpm.sh 的确切子命令）───────
if swtpm socket --help > /dev/null 2>&1; then
    ok "swtpm socket --help 可用（gnupg 消费的子命令）"
else
    bad "swtpm socket --help 失败"
fi

# ── 5. 以 gnupg 的方式在 TCP 上拉起模拟器 ─────────────────────────────
mkdir -p "$STATE_DIR" || { bad "无法创建状态目录 $STATE_DIR"; }

swtpm socket --tpm2 --daemon \
    --pid file="$STATE_DIR/swtpm.pid" \
    --server type=tcp,port="$SRV_PORT" \
    --ctrl type=tcp,port="$CTRL_PORT" \
    --flags not-need-init,startup-clear \
    --tpmstate dir="$STATE_DIR" > "$STATE_DIR/swtpm.log" 2>&1

if [ -s "$STATE_DIR/swtpm.pid" ]; then
    SWTPM_PID=$(cat "$STATE_DIR/swtpm.pid" 2>/dev/null | tr -dc '0-9')
fi

if [ -n "$SWTPM_PID" ] && kill -0 "$SWTPM_PID" 2>/dev/null; then
    ok "模拟器已拉起（daemon，pid=${SWTPM_PID}，TCP ${SRV_PORT}/${CTRL_PORT}）"
else
    bad "模拟器未能拉起（pid 文件/进程均不可用）：$(cat "$STATE_DIR/swtpm.log" 2>/dev/null | head -3 | tr '\n' ' ')"
fi

# ── 6. 控制通道端口可连接 ─────────────────────────────────────────────
connected=0
for _ in 1 2 3 4 5 6 7 8 9 10; do
    if (exec 3<>"/dev/tcp/127.0.0.1/${CTRL_PORT}") 2>/dev/null; then
        exec 3<&- 2>/dev/null || true
        exec 3>&- 2>/dev/null || true
        connected=1
        break
    fi
    sleep 1
done
if [ "$connected" = "1" ]; then
    ok "控制通道 TCP 127.0.0.1:${CTRL_PORT} 可连接（模拟器在服务）"
else
    bad "控制通道 TCP 127.0.0.1:${CTRL_PORT} 不可连接"
fi

# ── 7. 正常停止 ───────────────────────────────────────────────────────
if [ -n "$SWTPM_PID" ] && kill -0 "$SWTPM_PID" 2>/dev/null; then
    kill "$SWTPM_PID" 2>/dev/null || true
    sleep 1
    if kill -0 "$SWTPM_PID" 2>/dev/null; then
        bad "模拟器未能正常停止（pid=${SWTPM_PID}）"
    else
        ok "模拟器已正常停止"
    fi
    SWTPM_PID=""
else
    ok "模拟器已正常停止"
fi

echo
if [ "$FAILURES" -eq 0 ]; then
    echo "RESULT: PASS (${CHECKS} checks, 0 failures)"
    exit 0
else
    echo "RESULT: FAIL (${CHECKS} checks, ${FAILURES} failures)"
    exit 1
fi
