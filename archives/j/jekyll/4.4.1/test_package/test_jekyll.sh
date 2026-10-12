#!/bin/sh
# jekyll 消费者测试：用交付的 jekyll 构建一个最小站点，并断言渲染结果。
# 用法: test_jekyll.sh <site_dir> <out_dir>
set -eu

SITE="$1"
OUT="$2"

rm -rf "$SITE" "$OUT"
mkdir -p "$SITE/_layouts"

cat > "$SITE/_config.yml" <<'EOF'
title: jekyll test
EOF

cat > "$SITE/index.md" <<'EOF'
---
layout: default
title: home
---

Hello jekyll
EOF

cat > "$SITE/_layouts/default.html" <<'EOF'
<!DOCTYPE html><html><body><h1>{{ page.title }}</h1>{{ content }}</body></html>
EOF

jekyll build --source "$SITE" --destination "$OUT"

test -f "$OUT/index.html"
grep -q 'Hello jekyll' "$OUT/index.html"
grep -q '<h1>home</h1>' "$OUT/index.html"
echo "jekyll consumer test passed: $(tr -s ' \n' ' ' < "$OUT/index.html" | cut -c1-120)"
