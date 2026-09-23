#!/usr/bin/env bash
# test_package/test.sh — smoke test for conducteo executable
# Runs in conanrun env (PATH includes installed bin/)
# R34: 实质验证被测包二进制（offscreen 平台启动 GUI 事件循环）
set -euo pipefail

# 无显示环境：使用 offscreen 平台插件（OHOS 无 X11）
export QT_QPA_PLATFORM=offscreen

# conducteo 依赖 libQt6Core/libQt6Widgets → libc++_shared.so，位于
# OHOS SDK llvm/lib/aarch64-linux-ohos/（conanrun 的 LD_LIBRARY_PATH 不含
# 此目录，运行时 "Error loading shared library libc++_shared.so"）。
# SDK 路径可用环境变量 OHOS_SDK_LLVM_LIB 覆盖（默认取 CI profile 同路径）。
sdk_cxx="${OHOS_SDK_LLVM_LIB:-/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos}"
if [ -d "$sdk_cxx" ]; then
    export LD_LIBRARY_PATH="$sdk_cxx${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi

echo "[step] conducteo binary present"
# command -v 在 PATH 中找不到时返回非 0 且 BIN 为空；由下方 -z 检查兜底报错
# （set -e 下 `|| true` 防止 command 查找失败直接中断脚本）。
BIN="$(command -v conducteo || true)"
if [ -z "$BIN" ]; then
    echo "[fail] conducteo not found in PATH"
    exit 1
fi
echo "[ok] conducteo at $BIN"

echo "[step] conducteo GUI event loop (offscreen, 6s)"
# QT_QPA_PLATFORM=offscreen 下启动 Qt 事件循环；正常 GUI 应用会持续运行
# 至 timeout 被杀（退出码 124 = 事件循环正常存活），立即退出则异常。
set +e
timeout 6 "$BIN" >/dev/null 2>&1
rc=$?
set -e
if [ "$rc" -eq 124 ]; then
    echo "[ok] conducteo GUI event loop alive (timeout OK)"
else
    echo "[fail] conducteo exited rc=$rc"
    exit 1
fi

echo "[ok] conducteo smoke test OK"