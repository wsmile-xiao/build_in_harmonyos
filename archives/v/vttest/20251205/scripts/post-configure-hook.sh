#!/bin/bash
# post-configure-hook.sh — vttest 20251205
# 在每次 ./configure 之后执行
# 修复 config.status 的 TMPDIR/mktemp 临时目录权限问题（HMDFS sandbox）

set -e

BUILD_DIR="${1:-.}"

echo "  [hook] vttest: fixing config.status tmp directory for HarmonyOS HMDFS"

# Replace the TMPDIR/mktemp section in config.status with a simpler approach
# that uses the current directory for temp files
if [ -f "$BUILD_DIR/config.status" ]; then
    # Replace the mktemp-based temp directory creation with a local directory approach
    sed -i '/^# Create a (secure) tmp directory for tmp files.$/,/^$/c\
# Create a tmp directory for tmp files (HarmonyOS: mktemp-created dirs have permission issues)\
tmp=./_cs_tmp\
mkdir -p "$tmp"' "$BUILD_DIR/config.status"
    echo "  [hook] config.status tmp directory fixed"
fi

echo "  [hook] post-configure complete"
