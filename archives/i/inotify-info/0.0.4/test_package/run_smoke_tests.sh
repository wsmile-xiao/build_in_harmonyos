#!/bin/sh
# inotify-info test_package 冒烟断言（诚实断言）
# 用法: sh run_smoke_tests.sh </path/to/inotify-info>
#
# 只断言软件自身确定行为（对齐上游 ci.yaml 构建冒烟形态并加强）：
#   1. 可执行文件存在且可执行
#   2. --version 退出 0 且输出含 0.0.4
#   3. 裸跑（无参数）退出 0，输出含 INotify Limits 三项限额数值
#      （/proc/sys/fs/inotify/{max_queued_events,max_user_instances,max_user_watches}）
# 不断言 watch/instance 具体计数——那取决于运行环境状态，不是软件行为。
set -u

BIN="${1:-}"
TESTS=0
FAILED=0

ok()   { TESTS=$((TESTS + 1)); echo "ok - $1"; }
fail() { TESTS=$((TESTS + 1)); FAILED=$((FAILED + 1)); echo "not ok - $1"; }

# ── 1. 可执行文件存在且可执行 ──
if [ -n "$BIN" ] && [ -x "$BIN" ]; then
    ok "binary exists and is executable"
else
    fail "binary exists and is executable (got: '${BIN:-<empty>}')"
    echo "smoke summary: 1 assertion, 1 failed"
    exit 1
fi

# 工作目录（conan test() 的 cwd 为可写构建目录；mktemp 不可用时退回 cwd）
OUTDIR=$(mktemp -d 2>/dev/null) || OUTDIR=.

# ── 2. --version ──
VER_OUT=$("$BIN" --version 2>"$OUTDIR/ver.err")
VER_RC=$?
if [ "$VER_RC" -eq 0 ]; then
    ok "--version exits 0"
else
    fail "--version exits 0 (rc=$VER_RC)"
fi
case "$VER_OUT" in
    *0.0.4*) ok "--version output contains 0.0.4" ;;
    *) fail "--version output contains 0.0.4 (got: '$VER_OUT')" ;;
esac

# ── 3. 裸跑（无参数，对齐上游 build-with-gcc/zig/docker 冒烟）──
BARE_OUT="$OUTDIR/bare.out"
BARE_ERR="$OUTDIR/bare.err"
if command -v timeout >/dev/null 2>&1; then
    timeout 120 "$BIN" >"$BARE_OUT" 2>"$BARE_ERR"
    BARE_RC=$?
else
    "$BIN" >"$BARE_OUT" 2>"$BARE_ERR"
    BARE_RC=$?
fi
if [ "$BARE_RC" -eq 0 ]; then
    ok "bare run (no args) exits 0"
else
    fail "bare run (no args) exits 0 (rc=$BARE_RC)"
    echo "--- bare stderr ---"
    cat "$BARE_ERR"
fi

# INotify Limits 标题 + 三项 /proc/sys/fs/inotify 限额数值。
# 输出带 ANSI 颜色码（ESC[1;32m 前缀不含数字），正则 [^0-9]+ 直接跨过，
# 无需剥色即可断言数值存在。
if grep -q "INotify Limits" "$BARE_OUT" 2>/dev/null; then
    ok "bare run output contains 'INotify Limits'"
else
    fail "bare run output contains 'INotify Limits'"
fi

for key in max_queued_events max_user_instances max_user_watches; do
    if grep -E "${key}[^0-9]+[0-9]+" "$BARE_OUT" >/dev/null 2>&1; then
        ok "bare run reports ${key} with a numeric value"
    else
        fail "bare run reports ${key} with a numeric value"
    fi
done

if [ "$OUTDIR" != "." ]; then
    rm -rf "$OUTDIR"
fi

echo "smoke summary: ${TESTS} assertions, ${FAILED} failed"
if [ "$FAILED" -ne 0 ]; then
    exit 1
fi
exit 0
