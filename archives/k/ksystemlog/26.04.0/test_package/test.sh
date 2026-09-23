#!/bin/sh
# test_package/test.sh — ksystemlog 26.04.0 冒烟测试
# 用法: test.sh <ksystemlog 二进制>
# （由 test_package/conanfile.py 调用；QT_QPA_PLATFORM=offscreen 已由调用方注入）
set -eu

GUI="$1"

echo "[test] binary: $GUI"
test -x "$GUI"  || { echo "[test] ❌ ksystemlog not executable"; exit 1; }

# ---------- 断言 1: ksystemlog --version ----------
echo "[test] $GUI --version"
OUT="$("$GUI" --version 2>&1)" || {
    echo "[test] ❌ --version exited non-zero"
    echo "$OUT"
    exit 1
}
echo "$OUT"

case "$OUT" in
    *26.04.0*)
        echo "[test] ✅ --version reports 26.04.0"
        ;;
    *)
        echo "[test] ❌ unexpected version output"
        exit 1
        ;;
esac

# ---------- 断言 2: ksystemlog --help ----------
# QCommandLineParser/KAboutData 在 GUI 主窗口创建之前处理 --help；
# 打印 usage（含 "System Logs Viewer by KDE" 横幅）证明 ELF 加载、
# Qt 运行时初始化、KAboutData 命令行解析全部成功。
echo "[test] $GUI --help"
HELP="$("$GUI" --help 2>&1)" || {
    echo "[test] ❌ --help exited non-zero"
    echo "$HELP"
    exit 1
}
echo "$HELP" | head -3

case "$HELP" in
    *"System Logs Viewer by KDE"*)
        echo "[test] ✅ --help shows the ksystemlog usage banner"
        ;;
    *)
        echo "[test] ❌ unexpected --help output"
        exit 1
        ;;
esac

echo "[test] ALL SMOKE ASSERTIONS PASSED"
