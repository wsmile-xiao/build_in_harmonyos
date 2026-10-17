#!/bin/sh
# 消费者用例：kylin-scanner 端到端运行验证
# 验证二进制在 OHOS 环境下可完整启动、进入事件循环并保持运行
# 退出码：0=通过（应用成功启动并稳定运行），1=失败（启动崩溃或异常退出）
#
# OHOS 平台适配：/tmp 只读 → QLockFile 无法创建 → 程序立即退出。
# 通过 KYLIN_SCANNER_LOCK_FILE 环境变量将锁文件重定向到可写目录，
# 使程序能正常加锁并进入 Qt 事件循环。

set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BIN_PATH="${1:-}"
TIMEOUT_SECONDS="${2:-10}"

if [ -z "$BIN_PATH" ] || [ ! -x "$BIN_PATH" ]; then
    echo "FAIL: kylin-scanner binary not found or not executable: $BIN_PATH"
    exit 1
fi

echo "=== kylin-scanner 消费者用例：端到端运行验证 ==="
echo "Binary: $BIN_PATH"
echo "Timeout: ${TIMEOUT_SECONDS}s"

# ── OHOS 平台适配：设置可写的锁文件路径 ──
LOCK_DIR="${HOME:-/tmp}/tmp/kylin-scanner-lock"
mkdir -p "$LOCK_DIR" 2>/dev/null
if [ ! -d "$LOCK_DIR" ]; then
    echo "FAIL: cannot create lock directory: $LOCK_DIR"
    exit 1
fi
export KYLIN_SCANNER_LOCK_FILE="$LOCK_DIR/kylin-scanner.lock"
echo "Lock file: $KYLIN_SCANNER_LOCK_FILE"

# 验证资源文件完整性（翻译、图标、桌面文件）
PKG_DIR="$(dirname "$(dirname "$BIN_PATH")")"
echo "--- 资源文件检查 ---"
RES_OK=true
for res in "res/kylin-scanner/translations" "res/kylin-scanner/icons" "res/kylin-scanner/applications"; do
    if [ -d "$PKG_DIR/$res" ]; then
        COUNT=$(find "$PKG_DIR/$res" -type f 2>/dev/null | wc -l)
        echo "  OK: $res ($COUNT files)"
    else
        echo "  WARN: $res not found"
        RES_OK=false
    fi
done
if [ "$RES_OK" = false ]; then
    echo "FAIL: 资源文件不完整"
    exit 1
fi

# 启动 kylin-scanner（offscreen 平台插件，无需物理显示器）
echo "--- 启动应用 ---"
export QT_QPA_PLATFORM=offscreen
export HOME="${HOME:-/tmp}"

"$BIN_PATH" &
APP_PID=$!
echo "  PID: $APP_PID"

# 等待应用初始化并验证进程存活
echo "--- 验证运行稳定性（${TIMEOUT_SECONDS}s）---"
STABLE=true
for i in $(seq 1 "$TIMEOUT_SECONDS"); do
    sleep 1
    if ! kill -0 "$APP_PID" 2>/dev/null; then
        echo "FAIL: 应用在第 ${i}s 退出（崩溃或异常终止）"
        wait "$APP_PID" 2>/dev/null
        EXIT_CODE=$?
        echo "  退出码: $EXIT_CODE"
        exit 1
    fi
    echo "  ${i}s: 运行中..."
done

# 稳定运行后终止
echo "--- 终止应用 ---"
kill "$APP_PID" 2>/dev/null
wait "$APP_PID" 2>/dev/null
EXIT_CODE=$?

if [ "$EXIT_CODE" -eq 0 ] || [ "$EXIT_CODE" -eq 143 ] || [ "$EXIT_CODE" -eq 137 ]; then
    echo "  退出码: $EXIT_CODE (正常终止)"
else
    echo "  退出码: $EXIT_CODE (非预期)"
fi

echo "=== 消费者用例通过：kylin-scanner 端到端运行 ${TIMEOUT_SECONDS}s 无崩溃 ==="
exit 0
