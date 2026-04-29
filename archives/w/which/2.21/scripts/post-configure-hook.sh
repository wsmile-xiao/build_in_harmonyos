#!/bin/sh
# post-configure-hook.sh — 在每次 ./configure 之后执行
# 用于修复 config.status 中的 umask 077 问题 (E011)

SRC_DIR="$1"

if [ -z "$SRC_DIR" ]; then
    echo "Error: Usage: $0 <src_dir>"
    exit 1
fi

# 修复 config.status 中的 umask 077
if [ -f "$SRC_DIR/config.status" ]; then
    echo "  [hook] Fixing config.status umask 077 → umask 022 (E011)"
    sed -i 's/umask 077/umask 022/g' "$SRC_DIR/config.status"
fi

echo "  [hook] post-configure complete"