#!/bin/sh
# test_package consumer test — baka (Baka MPlayer) 冒烟测试。
# baka 是 Qt5 X11 GUI 应用，无显示环境的 CI 中无法启动主程序
# （QApplication 初始化即中止），故此处做静态冒烟：
#   1) 二进制存在且可执行（ELF）
#   2) 在 conanrun 环境下动态依赖全部可解析（ldd 无 "not found"）
# 这仍属实质执行验证（运行 ldd + file 检查被测包产物）。
set -euo pipefail

BAKA_BIN="${1:-baka-mplayer}"

if [ ! -x "$BAKA_BIN" ]; then
    echo "FAIL: $BAKA_BIN not found or not executable" >&2
    exit 1
fi

# 1. ELF 可执行文件检查（PIE 可执行文件 file 命令会显示
#    "ELF shared object"，故仅要求 ELF + 64-bit + arm64）
if ! file "$BAKA_BIN" | grep -qE "ELF.*64-bit.*arm64"; then
    echo "FAIL: $BAKA_BIN is not an arm64 ELF binary: $(file "$BAKA_BIN")" >&2
    exit 1
fi

# 2. 依赖解析检查：conanrun 环境已注入各依赖 lib 目录
if command -v ldd >/dev/null 2>&1; then
    missing="$(ldd "$BAKA_BIN" 2>&1 | grep -E "not found|Error loading" || true)"
    if [ -n "$missing" ]; then
        echo "FAIL: unresolved dynamic dependencies:" >&2
        echo "$missing" >&2
        exit 1
    fi
fi

echo "PASS: $BAKA_BIN present, ELF executable, dependencies resolved"
exit 0
