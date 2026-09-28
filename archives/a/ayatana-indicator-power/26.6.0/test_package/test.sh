#!/bin/sh
# test_package/test.sh — 端到端消费者用例 (rule12 整改)
#
# 用法:
#   冒烟模式:  test.sh <path-to-ayatana-indicator-power-service>
#   端到端模式: test.sh <path-to-ayatana-indicator-power-service> \
#                      <path-to-test_consumer> <compiled-schema-dir>
#
# 冒烟模式: 真实执行被测二进制 --version（断言含 26.6.0）+ --help。
# 端到端模式: 真实消费者程序 test_consumer 经 GDBusServer 私有 peer-bus
#             (unix:abstract=) 拉起服务，驱动 Testing mock 电池 80%，
#             再经真实 D-Bus 属性断言 Battery.PowerPercentage=80 /
#             IsDischarging=true / PowerLevel=ok（8 处断言，见
#             test_consumer.c），真实进程间通信，非冒烟断言。
set -u

if [ "$#" -lt 1 ]; then
    echo "[test] 用法: test.sh <service-binary> [<test_consumer> [<schema-dir>]]" >&2
    exit 2
fi
BINARY="$1"
CONSUMER="${2:-}"
SCHEMA_DIR="${3:-}"

# ── 冒烟检查 (始终执行) ──────────────────────────────────────
echo "[test] --version"
OUT="$("$BINARY" --version 2>&1)" || {
    echo "[test] ❌ --version 退出码非 0" >&2
    echo "$OUT" >&2
    exit 1
}
echo "$OUT"
echo "$OUT" | grep -q "26.6.0" || {
    echo "[test] ❌ --version 输出缺少版本号 26.6.0" >&2
    exit 1
}
echo "[test] ✅ --version 含版本号 26.6.0"

echo "[test] --help"
"$BINARY" --help >/dev/null 2>&1 || {
    echo "[test] ❌ --help 失败" >&2
    exit 1
}
echo "[test] ✅ --help OK"

# ── 端到端消费者用例 (提供消费者二进制与 schema 时执行) ──────
if [ -n "$CONSUMER" ] && [ -n "$SCHEMA_DIR" ]; then
    if [ ! -x "$CONSUMER" ]; then
        echo "[test] ❌ 消费者二进制不存在: $CONSUMER" >&2
        exit 1
    fi
    if [ ! -f "$SCHEMA_DIR/gschemas.compiled" ]; then
        echo "[test] ❌ schema 目录缺少 gschemas.compiled: $SCHEMA_DIR" >&2
        exit 1
    fi
    echo "[test] 端到端消费者用例（GDBusServer peer-bus 驱动服务）..."
    GSETTINGS_SCHEMA_DIR="$SCHEMA_DIR" GSETTINGS_BACKEND=memory \
        "$CONSUMER" "$BINARY"
    RC=$?
    if [ "$RC" -ne 0 ]; then
        echo "[test] ❌ 端到端消费者用例失败 (exit $RC)" >&2
        exit "$RC"
    fi
    echo "[test] ✅ 端到端消费者用例通过（8 处断言）"
else
    echo "[test] 未提供消费者二进制/schema 目录，仅执行冒烟检查"
fi

echo "[test] 全部通过"
exit 0
