#!/data/service/hnp/bin/bash
# test_package/test.sh — 鸿蒙特有冒烟测试：在 OH 设备上以 offscreen 平台启动
# kapow 二进制，验证 Qt 初始化与主窗口构造成功（无崩溃）。
set -eu

BIN="${CONAN_BIN_DIRS:-.}/kapow"
if [ ! -x "$BIN" ]; then
    case "$PATH" in
        *) for d in $(echo "$PATH" | tr ':' ' '); do
               [ -x "$d/kapow" ] && { BIN="$d/kapow"; break; }
           done ;;
    esac
fi
[ -x "$BIN" ] || { echo "kapow binary not found"; exit 1; }

echo "[test] $BIN (offscreen smoke test)"
set +e
timeout 10 env QT_QPA_PLATFORM=offscreen "$BIN" "$@"
rc=$?
set -e
# Qt 初始化失败会立即非 0 退出；超时(124)或正常退出都代表已成功初始化并进入事件循环
if [ "$rc" -eq 0 ] || [ "$rc" -eq 124 ]; then
    echo "[test] kapow offscreen init OK (rc=$rc)"
    exit 0
fi
echo "[test] kapow offscreen init FAILED rc=$rc"
exit "$rc"
