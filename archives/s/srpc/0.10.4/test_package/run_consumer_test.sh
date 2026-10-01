#!/bin/sh
# 消费者往返测试：后台起 srpc 服务端 → 前台跑客户端 → 断言结果
set -euo pipefail

SRV="$1"
CLI="$2"
PORT="${3:-14120}"
LOG="$(dirname "$CLI")/echo_server.log"

"$SRV" "$PORT" >"$LOG" 2>&1 &
SRV_PID=$!

# 等待服务端监听（最多 20s）
i=0
while [ "$i" -lt 100 ]; do
	if grep -q "SERVER_READY" "$LOG" 2>/dev/null; then
		break
	fi
	i=$((i + 1))
	sleep 0.2
done

RC=0
"$CLI" "$PORT" || RC=$?

kill "$SRV_PID" 2>/dev/null || true   # 服务端可能已自行退出
wait "$SRV_PID" 2>/dev/null || true   # 已被 kill，wait 返回非 0 属预期

echo "--- echo_server.log ---"
cat "$LOG"
echo "--- client rc=$RC ---"
exit "$RC"
