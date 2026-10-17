#!/bin/sh
# test_package consumer test — sioyek（Qt5 + mupdf PDF 阅读器）冒烟测试。
# sioyek --version 在 main() 中 QApplication 构造之前处理（main.cpp:662），
# 无显示环境可真实运行主程序，故做三层冒烟：
#   1) 二进制存在且可执行（arm64 ELF）
#   2) 在 conanrun 环境下动态依赖全部可解析（ldd 无 "not found"）
#   3) --version 实际运行输出 "sioyek 2.0.0"
set -eu

SIOYEK_BIN="${1:-sioyek}"

if [ ! -x "$SIOYEK_BIN" ]; then
    echo "FAIL: $SIOYEK_BIN not found or not executable" >&2
    exit 1
fi

# 1. ELF 可执行文件检查（PIE 可执行文件 file 命令会显示
#    "ELF shared object"，故仅要求 ELF + 64-bit + arm64）
if ! file "$SIOYEK_BIN" | grep -qE "ELF.*64-bit.*arm64"; then
    echo "FAIL: $SIOYEK_BIN is not an arm64 ELF binary: $(file "$SIOYEK_BIN")" >&2
    exit 1
fi

# 2. 依赖解析检查：conanrun 环境已注入各依赖 lib 目录
if command -v ldd >/dev/null 2>&1; then
    missing="$(ldd "$SIOYEK_BIN" 2>&1 | grep -E "not found|Error loading" || true)"
    if [ -n "$missing" ]; then
        echo "FAIL: unresolved dynamic dependencies:" >&2
        echo "$missing" >&2
        exit 1
    fi
fi

# 3. --version 实际运行（main.cpp 在 QApplication 之前处理 --version）
version_output="$("$SIOYEK_BIN" --version 2>&1)"
echo "$version_output"
if ! echo "$version_output" | grep -q "^sioyek 2.0.0$"; then
    echo "FAIL: unexpected --version output: $version_output" >&2
    exit 1
fi

echo "PASS: $SIOYEK_BIN ELF executable, dependencies resolved, --version OK"
exit 0
