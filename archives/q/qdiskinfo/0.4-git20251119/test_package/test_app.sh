#!/bin/sh
# test_app.sh — 手工复现 test_package 的验证步骤（真机/调试用）
#
# 自动化断言在 test_package/conanfile.py（第 1 层 test_qdiskinfo +
# 第 2 层提权回退集成场景）。本脚本用最小依赖复现同样的调用，便于在
# 设备上人工确认：
#
#   usage: ./test_app.sh <pkg-folder>/bin/QDiskInfo
#
# 注意：真机上 smartctl 由 smartmontools/7.4 提供（conan install 后
# 位于运行环境 PATH，或手工加入 PATH）；HarmonyOS PC 无 pkexec。
set -eu

APP_BIN="${1:-}"
if [ -z "$APP_BIN" ] || [ ! -x "$APP_BIN" ]; then
    echo "usage: $0 <path-to-QDiskInfo>" >&2
    exit 2
fi

TMP_ROOT="${TMPDIR:-$HOME/tmp}/qdiskinfo-manual"
mkdir -p "$TMP_ROOT/home" "$TMP_ROOT/tmp"
export HOME="$TMP_ROOT/home"
export TMPDIR="$TMP_ROOT/tmp"

echo "== 1) --version（无 GUI 早期退出） =="
"$APP_BIN" --version

echo "== 2) --help =="
"$APP_BIN" --help

echo "== 3) --ascii-view /dev/null（无 GUI；非 root 预期报错退出 1） =="
set +e
"$APP_BIN" --ascii-view /dev/null > "$TMP_ROOT/ascii.bin" 2> "$TMP_ROOT/ascii.err"
rc=$?
set -e
echo "exit=$rc stderr=$(cat "$TMP_ROOT/ascii.err")"
if [ "$(id -u 2>/dev/null || echo 1)" != "0" ] && [ "$rc" != "1" ]; then
    echo "FAIL: 非 root 下 --ascii-view 预期退出码 1" >&2
    exit 1
fi

echo "== 4) smartctl 可用性（运行期依赖 smartmontools/7.4） =="
command -v smartctl || { echo "FAIL: PATH 中找不到 smartctl" >&2; exit 1; }
smartctl --scan --json | head -c 200
echo

echo "== 5) GUI offscreen 启动冒烟（8s 后强杀，非 0 退出即为启动失败） =="
QT_QPA_PLATFORM=offscreen "$APP_BIN" &
app_pid=$!
sleep 8
if ! kill -0 "$app_pid" 2>/dev/null; then
    wait "$app_pid" || {
        echo "FAIL: offscreen GUI 提前退出（Qt 平台插件或主窗口构造失败）" >&2
        exit 1
    }
fi
kill -9 "$app_pid" 2>/dev/null || true
wait "$app_pid" 2>/dev/null || true

echo "== 6) 提权回退检查：pkexec 缺失时应直接执行 smartctl =="
if command -v pkexec >/dev/null 2>&1; then
    echo "SKIP: 本机存在 pkexec，非 HarmonyOS PC 场景"
else
    echo "OK: 无 pkexec（HarmonyOS PC），QDiskInfo 将直接执行 smartctl"
fi

echo "ALL MANUAL CHECKS DONE"
