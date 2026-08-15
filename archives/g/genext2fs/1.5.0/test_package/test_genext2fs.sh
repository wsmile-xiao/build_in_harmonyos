#!/bin/sh
# test_genext2fs.sh — genext2fs test_package 测试脚本
# 验证 genext2fs 可执行 + 实际生成 ext2 镜像（R34：实质调用被测包）
#
# 用法: sh test_genext2fs.sh <bin_dir> [<tmp_dir>]
set -e

if [ $# -lt 1 ]; then
    echo "usage: $0 <bin_dir> [<tmp_dir>]" >&2
    exit 2
fi
BIN_DIR="$1"
GENEXT2FS="$BIN_DIR/genext2fs"

echo "== 1. 可执行性检查 =="
if ! "$GENEXT2FS" --version >/dev/null 2>&1 && ! "$GENEXT2FS" -V >/dev/null 2>&1; then
    echo "FAIL: genext2fs not executable" >&2
    exit 1
fi

echo "== 2. 实际生成 ext2 镜像 =="
# 用传入的 build_folder 建临时目录（/tmp 在部分沙箱只读，mktemp 不可靠）
if [ $# -ge 2 ]; then
    TMP_DIR="$2/genext2fs-test"
else
    TMP_DIR=$(mktemp -d 2>/dev/null || echo "genext2fs-test")
fi
# 源目录与输出镜像分目录（避免镜像文件被当作源内容扫描），-b 4096 保证空间
mkdir -p "$TMP_DIR/src" "$TMP_DIR/img"
printf 'genext2fs test\n' > "$TMP_DIR/src/hello.txt"
IMG="$TMP_DIR/img/test.ext2"
if "$GENEXT2FS" -b 4096 -d "$TMP_DIR/src" "$IMG" >/dev/null 2>&1; then
    SIZE=$(wc -c < "$IMG" 2>/dev/null || echo 0)
    if [ "$SIZE" -gt 0 ] 2>/dev/null; then
        echo "OK: genext2fs generated ext2 image ($SIZE bytes)"
    else
        echo "FAIL: image generated but size is 0" >&2
        rm -rf "$TMP_DIR"
        exit 1
    fi
else
    echo "FAIL: image generation failed (genext2fs -b 4096 -d <src> <img>)" >&2
    rm -rf "$TMP_DIR"
    exit 1
fi
rm -rf "$TMP_DIR"
