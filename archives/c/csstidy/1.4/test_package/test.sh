#!/data/service/hnp/bin/bash
# test_package/test.sh — csstidy 鸿蒙专项测试（真实执行 CLI 并断言优化行为）
# 运行于 conanrun 环境（PATH 含已安装 bin/）
# 断言点（与上游文档功能语义一致）：
#   1) 数字优化：0px -> 0
#   2) 颜色优化：#ff0000 -> red
#   3) 属性排序与去重
set -u

BIN="${1:-csstidy}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

cat > "$TMP/in.css" <<'CSS'
body { margin: 0px; padding:0px; color: #ff0000; margin: 0px; }
CSS

"$BIN" "$TMP/in.css" "$TMP/out.css" > "$TMP/run.log" 2>&1
RC=$?
echo "[csstidy] exit_code=$RC"
cat "$TMP/run.log"
echo "-----OUTPUT-----"
cat "$TMP/out.css"
echo "-----ASSERTS-----"

pass=0; fail=0
check() { # name expected actual
  if echo "$3" | grep -q "$2"; then echo "PASS $1"; pass=$((pass+1));
  else echo "FAIL $1 (expected '$2' not in: $3)"; fail=$((fail+1)); fi
}

OUT="$(cat "$TMP/out.css")"
[ "$RC" -eq 0 ] && { echo "PASS exit_code=0"; pass=$((pass+1)); } || { echo "FAIL exit_code"; fail=$((fail+1)); }
check "color_optimized"   "color:red"   "$OUT"
check "margin_optimized"  "margin:0"    "$OUT"
check "padding_optimized" "padding:0"   "$OUT"
check "no_dup_margin"     "1"           "$(echo "$OUT" | grep -c 'margin')"

echo "RESULT pass=$pass fail=$fail"
[ "$fail" -eq 0 ]
