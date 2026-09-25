#!/bin/sh
# test_package/test.sh — ktuberling 26.04.0 冒烟测试
# 用法: test.sh <ktuberling 二进制>
# （由 test_package/conanfile.py 调用；QT_QPA_PLATFORM=offscreen 已由调用方注入）
set -eu

GUI="$1"

echo "[test] binary: $GUI"
test -x "$GUI" || { echo "[test] ❌ ktuberling not executable"; exit 1; }

# ---------- 断言 1: ktuberling --version ----------
# KAboutData::setupCommandLine 在 GUI 主窗口创建前处理 --version
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

echo "[test] ALL SMOKE ASSERTIONS PASSED"
