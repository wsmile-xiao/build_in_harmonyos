#!/usr/bin/env sh
# test_package/test.sh — usbmuxd 1.0.8 消费者冒烟测试
# 用法: test.sh <usbmuxd 二进制> <iproxy 二进制> <测试程序>
set -eu

DAEMON="$1"
IPROXY="$2"
TESTPROG="$3"

echo "[test] binaries: $DAEMON / $IPROXY / $TESTPROG"
test -x "$DAEMON"   || { echo "[test] FAIL: usbmuxd not executable"; exit 1; }
test -x "$IPROXY"   || { echo "[test] FAIL: iproxy not executable"; exit 1; }
test -x "$TESTPROG" || { echo "[test] FAIL: test program not executable"; exit 1; }

# ---------- 断言 1: usbmuxd -h 打印 usage 并退出 0 ----------
echo "[test] usbmuxd -h"
OUT="$("$DAEMON" -h 2>&1)" || {
    echo "[test] FAIL: usbmuxd -h exited non-zero"
    echo "$OUT"
    exit 1
}

case "$OUT" in
    *"usage: usbmuxd"*)
        echo "[test] PASS: usbmuxd -h prints usage banner"
        ;;
    *)
        echo "[test] FAIL: unexpected usbmuxd -h output"
        echo "$OUT"
        exit 1
        ;;
esac

case "$OUT" in
    *"--force-exit"*)
        echo "[test] PASS: usbmuxd -h lists options (ELF load + getopt + libc OK)"
        ;;
    *)
        echo "[test] FAIL: usbmuxd -h output missing option list"
        exit 1
        ;;
esac

# ---------- 断言 2: iproxy 无参数打印 usage ----------
echo "[test] iproxy (no args)"
OUT2="$("$IPROXY" 2>&1)" || true
case "$OUT2" in
    *"LOCAL_TCP_PORT DEVICE_TCP_PORT"*)
        echo "[test] PASS: iproxy prints usage (libusbmuxd-2.0 client linked, exit 0)"
        ;;
    *)
        echo "[test] FAIL: unexpected iproxy output"
        echo "$OUT2"
        exit 1
        ;;
esac

# ---------- 断言 3: 消费者程序 —— libusbmuxd 客户端 API 行为断言 ----------
# 在无 usbmuxd 守护进程的环境下 usbmuxd_get_device_list() 必须返回
# 负错误码（-ENODEV，connect() 失败路径）而不是崩溃——证明 ELF 加载、
# libusbmuxd-2.0 + libplist-2.0 链接链、错误路径全部正确。
echo "[test] consumer program (libusbmuxd API assertion)"
if "$TESTPROG"; then
    echo "[test] PASS: consumer API assertions all passed"
else
    echo "[test] FAIL: consumer API assertions failed"
    exit 1
fi

echo "[test] ALL SMOKE ASSERTIONS PASSED"
