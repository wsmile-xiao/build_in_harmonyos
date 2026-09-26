#!/bin/sh
# wev test_package — 真实运行 wev 二进制（消费验证）
#   1) wev -h         : 打印 usage 并退出 0（无需显示服务器）
#   2) wev（无 display）: wl_display_connect 失败路径 -> 退出 1 + 报错文本
#   3) readelf        : 确认二进制动态链接了 libwayland-client（依赖链已解析）
set -u

fail() { echo "FAIL: $1" >&2; exit 1; }
pass() { echo "PASS: $1"; }

WEV_BIN=$(command -v wev 2>/dev/null || true)
[ -n "$WEV_BIN" ] || fail "PATH 中找不到 wev 二进制"

# 超时保护：wev 是事件查看器，若意外连上合成器会常驻
RUN=""
command -v timeout >/dev/null 2>&1 && RUN="timeout 20"

# 1) usage 路径
usage_out=$($RUN "$WEV_BIN" -h 2>&1); usage_rc=$?
[ "$usage_rc" -eq 0 ] || fail "wev -h 期望退出码 0，实际 $usage_rc（输出: $usage_out）"
echo "$usage_out" | grep -q "Usage: wev" || fail "wev -h 未打印预期 usage 行: $usage_out"
pass "wev -h 打印 usage 并以 0 退出"

# 2) 无显示服务器：清掉 wayland 相关环境变量，强制走连接失败路径
conn_out=$(env -u WAYLAND_DISPLAY -u WAYLAND_SOCKET -u XDG_RUNTIME_DIR \
    -u DISPLAY $RUN "$WEV_BIN" 2>&1); conn_rc=$?
[ "$conn_rc" -eq 1 ] || fail "wev 无显示服务器时期望退出码 1，实际 $conn_rc（输出: $conn_out）"
echo "$conn_out" | grep -q "Failed to connect to Wayland display" \
    || fail "wev 缺少连接失败提示: $conn_out"
pass "wev 无显示服务器时按预期报错退出（rc=1）"

# 3) 运行时依赖确实被动态链接（wayland-client / xkbcommon）
if command -v readelf >/dev/null 2>&1; then
    dynamic=$(readelf -d "$WEV_BIN" 2>/dev/null || true)
    echo "$dynamic" | grep -q "libwayland-client" \
        || fail "wev 未动态链接 libwayland-client"
    echo "$dynamic" | grep -q "libxkbcommon" \
        || fail "wev 未动态链接 libxkbcommon"
    pass "readelf 确认 wev 链接 libwayland-client 与 libxkbcommon"
fi

echo "all wev test_package assertions passed"
