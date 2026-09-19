#!/bin/sh
# test_package 功能测试：验证 critter 二进制可运行 + --version 冒烟
# 用法: test.sh <critter路径> <输出目录>
# 依赖: 0004 补丁使 --version 在 SDL/GL 初始化前输出后退出（无头环境可跑）
set -e

CRITTER="$1"
OUT_DIR="$2"

if [ ! -x "$CRITTER" ]; then
    echo "[fail] critter not found at $CRITTER"
    exit 1
fi

# 正例：--version 应输出 "Critical_Mass 1.0.2"（退出码为 0）
set +e
"$CRITTER" --version > "$OUT_DIR/version.out" 2>&1
VERSION_RC=$?
set -e

if ! grep -q "Critical_Mass 1.0.2" "$OUT_DIR/version.out"; then
    echo "[fail] critter --version did not print banner (rc=$VERSION_RC)"
    cat "$OUT_DIR/version.out"
    exit 1
fi
if [ "$VERSION_RC" -ne 0 ]; then
    echo "[fail] critter --version exited with rc=$VERSION_RC (expected 0)"
    exit 1
fi
echo "[pass] critter --version prints 'Critical_Mass 1.0.2' (rc=$VERSION_RC)"

exit 0
