#!/bin/sh
# 一键应用所有补丁
# 用法：cd {source-dir} && sh /path/to/patches/apply-patches.sh

PATCH_DIR="$(cd "$(dirname "$0")" && pwd)"
SERIES="$PATCH_DIR/series"

echo "=== 应用鸿蒙适配补丁 ==="

if [ -f "$SERIES" ]; then
    while IFS= read -r line; do
        # 跳过空行和注释
        case "$line" in
            ""|\#*) continue ;;
        esac
        patch_file="$PATCH_DIR/$line"
        if [ -f "$patch_file" ]; then
            echo "应用: $line"
            patch -p1 < "$patch_file" || {
                echo "❌ 补丁 $line 应用失败"
                exit 1
            }
        else
            echo "⚠️ 补丁文件不存在: $patch_file"
        fi
    done < "$SERIES"
else
    echo "使用 quilt apply 或手动应用 patches/ 下的补丁"
    for p in "$PATCH_DIR/patches/"*.patch; do
        [ -f "$p" ] || continue
        echo "应用: $(basename "$p")"
        patch -p1 < "$p" || {
            echo "❌ 补丁 $(basename "$p") 应用失败"
            exit 1
        }
    done
fi

echo "=== 所有补丁已应用 ==="
