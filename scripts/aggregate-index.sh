#!/bin/sh
# aggregate-index.sh - 从所有 _meta.yaml 聚合生成 _index.yaml
# 用法：./scripts/aggregate-index.sh

set -e

ARCHIVES_DIR="$(cd "$(dirname "$0")/../archives" && pwd)"
INDEX_FILE="$ARCHIVES_DIR/_index.yaml"

echo "# 软件索引（自动生成，勿手动编辑）" > "$INDEX_FILE"
echo "# 生成时间: $(date '+%Y-%m-%d %H:%M')" >> "$INDEX_FILE"
echo "" >> "$INDEX_FILE"
echo "software_index:" >> "$INDEX_FILE"

count=0
for meta in "$ARCHIVES_DIR"/?/*/*/_meta.yaml; do
    [ -f "$meta" ] || continue
    count=$((count + 1))
    
    # 读取字段
    sw=$(grep '^software:' "$meta" | head -1 | sed 's/software: *//')
    ver=$(grep '^version:' "$meta" | head -1 | sed 's/version: *//')
    letter=$(grep '^letter:' "$meta" | head -1 | sed 's/letter: *//')
    status=$(grep '^status:' "$meta" | head -1 | sed 's/status: *//')
    build_sys=$(grep '^build_system:' "$meta" | head -1 | sed 's/build_system: *//')
    compat=$(grep '^compatibility:' "$meta" | head -1 | sed 's/compatibility: *//')
    patches=$(grep '^patches_count:' "$meta" | head -1 | sed 's/patches_count: *//')
    path=$(grep '^archive_path:' "$meta" | head -1 | sed 's/archive_path: *//')
    
    echo "" >> "$INDEX_FILE"
    echo "  - software: $sw" >> "$INDEX_FILE"
    echo "    version: $ver" >> "$INDEX_FILE"
    echo "    letter: $letter" >> "$INDEX_FILE"
    echo "    status: $status" >> "$INDEX_FILE"
    echo "    build_system: $build_sys" >> "$INDEX_FILE"
    echo "    compatibility: $compat" >> "$INDEX_FILE"
    echo "    patches: $patches" >> "$INDEX_FILE"
    echo "    path: $path" >> "$INDEX_FILE"
done

echo "" >> "$INDEX_FILE"
echo "# 共 $count 个软件版本" >> "$INDEX_FILE"

echo "✅ 已生成 $INDEX_FILE（$count 个软件）"
