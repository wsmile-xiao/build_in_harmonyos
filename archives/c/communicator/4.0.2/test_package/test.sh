#!/data/service/hnp/bin/bash
# test_package/test.sh — 鸿蒙特有冒烟测试：在 OH 设备上以 offscreen 平台启动
# communicator 二进制，验证 Qt 初始化与 QML 引擎加载成功（无崩溃）。
set -eu

BIN="${CONAN_BIN_DIRS:-.}/communicator"
if [ ! -x "$BIN" ]; then
    case "$PATH" in
        *) for d in $(echo "$PATH" | tr ':' ' '); do
               [ -x "$d/communicator" ] && { BIN="$d/communicator"; break; }
           done ;;
    esac
fi
[ -x "$BIN" ] || { echo "communicator binary not found"; exit 1; }

echo "[test] $BIN (offscreen smoke test)"
# QML modules live in separate conan package prefixes (qtdeclarative qml/,
# MauiKit lib/qml) while QtCore's baked QmlImportsPath points into qtbase
# (no qml/). The test harness passes them via CONAN_QML_IMPORT_PATH.
if [ -n "${CONAN_QML_IMPORT_PATH:-}" ]; then
    export QML2_IMPORT_PATH="$CONAN_QML_IMPORT_PATH"
    export QML_IMPORT_PATH="$CONAN_QML_IMPORT_PATH"
fi
set +e
timeout 10 env QT_QPA_PLATFORM=offscreen "$BIN" "$@"
rc=$?
set -e
# Qt 初始化失败会立即非 0 退出；超时(124)或正常退出都代表已成功初始化并进入事件循环
if [ "$rc" -eq 0 ] || [ "$rc" -eq 124 ]; then
    echo "[test] communicator offscreen init OK (rc=$rc)"
    exit 0
fi
echo "[test] communicator offscreen init FAILED rc=$rc"
exit "$rc"
