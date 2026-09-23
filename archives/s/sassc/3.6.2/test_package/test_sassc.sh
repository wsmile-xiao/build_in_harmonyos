#!/bin/sh
# R34: 真实执行 sassc 编译一段 SCSS 并校验 CSS 输出（非空壳）。
# sassc 在 PATH 上（test_package 的 VirtualRunEnv/conanrun 环境）。
# 临时文件写当前工作目录（test_package 构建目录，可写；OHOS /tmp 只读）。
set -e
SCSS="sassc_test_$$.scss"
CSS="sassc_test_$$.css"
trap 'rm -f "$SCSS" "$CSS"' EXIT

cat > "$SCSS" <<'EOF'
$color: #ff0000;
.foo { color: $color; }
EOF

sassc "$SCSS" "$CSS"

# 校验：变量插值生效，输出包含预期 CSS
grep -q "color: #ff0000" "$CSS"
echo "OK: sassc compiled SCSS (variable interpolation) to CSS"
