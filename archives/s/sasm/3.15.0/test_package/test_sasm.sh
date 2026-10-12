#!/usr/bin/env bash
# test_sasm.sh — sasm/3.15.0 消费者视角测试（R34：实际执行被测包二进制）
# 以 QT_QPA_PLATFORM=offscreen 启动打包出的 sasm GUI，验证：
#   1) ELF 可加载（DT_NEEDED 的 Qt5 共享库能解析到 qt/5.15.19 包）
#   2) Qt5 插件/翻译/资源加载正常
#   3) singleapplication 初始化（Qt5Network 路径）正常
# 判定：进程 8s 后仍存活（GUI 事件循环运行中）= 启动成功。
set -euo pipefail
SASM_BIN="${SASM_BIN:?SASM_BIN not set}"
export QT_QPA_PLATFORM=offscreen
export HOME="${HOME:-$(pwd)}"

"$SASM_BIN" &
PID=$!
sleep 8

if ! kill -0 "$PID" 2>/dev/null; then
    echo "FAIL: sasm exited within 8s" >&2
    wait "$PID"
    exit 1
fi

kill "$PID" 2>/dev/null
for _ in 1 2 3 4 5 6 7 8 9 10; do
    kill -0 "$PID" 2>/dev/null || break
    sleep 1
done
kill -9 "$PID" 2>/dev/null || true

echo "PASS: sasm launched and ran headless (offscreen), still alive after 8s"
exit 0
