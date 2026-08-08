#!/bin/sh
# test_package 功能测试：用 milkycli 将示例曲目导出 WAV 并校验产物
# 用法: test.sh <milkycli路径> <xm目录> <输出目录>
set -e

MILKYCLI="$1"
XM_DIR="$2"
OUT_DIR="$3"

if [ ! -x "$MILKYCLI" ]; then
    echo "[fail] milkycli not found at $MILKYCLI"
    exit 1
fi

XM_FILE=$(ls "$XM_DIR"/*.xm 2>/dev/null | head -1)
if [ -z "$XM_FILE" ]; then
    echo "[fail] no example .xm song in $XM_DIR"
    exit 1
fi

OUT="$OUT_DIR/export.wav"
"$MILKYCLI" -output "$OUT" "$XM_FILE" || {
    echo "[fail] milkycli export failed"
    exit 1
}

if [ ! -f "$OUT" ]; then
    echo "[fail] $OUT not produced"
    exit 1
fi

SIZE=$(wc -c < "$OUT")
if [ "$SIZE" -le 44 ]; then
    echo "[fail] exported wav too small: $SIZE bytes"
    exit 1
fi

echo "[pass] milkycli exported $(basename "$XM_FILE") -> wav ($SIZE bytes)"
