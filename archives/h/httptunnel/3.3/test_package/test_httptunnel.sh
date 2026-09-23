#!/bin/sh
# test_httptunnel.sh — 消费者测试：真实运行 hts/htc 并断言行为
# 用法: test_httptunnel.sh <hts_bin> <htc_bin> <fixture_dir>
#
# 断言:
# 1. hts --version 输出版本
# 2. htc --version 输出版本
# 3. htc 前转端口接受 TCP 连接（真实 accept）
# 4. hts 隧道端口接受 TCP 连接（真实 accept）
# 5. 隧道握手后 hts 向目的端口转发了连接（echo 服务器写 marker 文件）
#
# 已知 OHOS 限制（详见 notes.md）：隧道数据回传路径在 OHOS 上受 poll()
# 返回异常 revents 影响不可用，本测试不断言数据回传。

set -u

HTS="$1"
HTC="$2"
FIX="$3"
PY=python3

WORK="$PWD/htp-test-$$"
mkdir -p "$WORK"
MARKER="$WORK/dest_marker"

HTS_PID=""; HTC_PID=""; SRV_PID=""
cleanup() {
    [ -n "$HTS_PID" ] && kill -9 "$HTS_PID" 2>/dev/null
    [ -n "$HTC_PID" ] && kill -9 "$HTC_PID" 2>/dev/null
    [ -n "$SRV_PID" ] && kill -9 "$SRV_PID" 2>/dev/null
    rm -rf "$WORK"
}
trap cleanup EXIT INT TERM

# --- Test 1/2: version output ---
V1=$("$HTS" --version 2>&1)
echo "$V1" | grep -q "httptunnel" || { echo "FAIL: hts version output missing: $V1"; exit 1; }
echo "PASS: hts version ($V1)"

V2=$("$HTC" --version 2>&1)
echo "$V2" | grep -q "httptunnel" || { echo "FAIL: htc version output missing: $V2"; exit 1; }
echo "PASS: htc version ($V2)"

# --- real server with real destination ---
"$PY" "$FIX/echo_srv.py" 18022 "$MARKER" &
SRV_PID=$!
sleep 1

"$HTS" -w -F 127.0.0.1:18022 18023 >"$WORK/hts.log" 2>&1 &
HTS_PID=$!
sleep 2
kill -0 "$HTS_PID" 2>/dev/null || { echo "FAIL: hts not running"; cat "$WORK/hts.log"; exit 1; }
echo "PASS: hts server running"

"$HTC" -w -F 18024 -k 2 127.0.0.1:18023 >"$WORK/htc.log" 2>&1 &
HTC_PID=$!
sleep 2
kill -0 "$HTC_PID" 2>/dev/null || { echo "FAIL: htc not running"; cat "$WORK/htc.log"; exit 1; }
echo "PASS: htc client running"

# --- Test 3: htc forward port accepts a TCP connection (triggers tunnel) ---
"$PY" "$FIX/probe_cli.py" 18024 --connect-only || { echo "FAIL: htc forward port not accepting"; exit 1; }
echo "PASS: htc forward port accepted connection"

# --- Test 5: hts forwarded the tunnel to the destination ---
i=0
while [ $i -lt 15 ]; do
    [ -f "$MARKER" ] && break
    sleep 1
    i=$((i + 1))
done
if [ -f "$MARKER" ]; then
    echo "PASS: hts forwarded tunnel to destination (marker written)"
else
    echo "FAIL: destination marker missing after 15s"
    echo "--- hts.log ---"; cat "$WORK/hts.log" 2>/dev/null
    echo "--- htc.log ---"; cat "$WORK/htc.log" 2>/dev/null
    exit 1
fi

# --- Test 4: hts tunnel port accepts a TCP connection ---
"$PY" "$FIX/probe_cli.py" 18023 --connect-only || { echo "FAIL: hts tunnel port not accepting"; exit 1; }
echo "PASS: hts tunnel port accepted connection"

echo "All tests passed."
