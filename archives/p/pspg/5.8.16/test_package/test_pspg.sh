#!/bin/bash
# 消费者测试 — pspg 5.8.16
# 用法: test_pspg.sh <包内 pspg 绝对路径>
# 6 项断言，全部离线，真实执行被适配工具（R34）。
# 非 tty stdout 下 pspg --csv/--tsv 走非交互渲染路径（pspg.c:2997），
# 不初始化 ncurses，可离线确定性验证真实数据管线。
set -u
PSPG="$1"
HERE="$(cd "$(dirname "$0")" && pwd)"
TMP="$(mktemp -d)" || exit 1
trap 'rm -rf "$TMP"' EXIT
PASS=0
FAIL=0

ok() { PASS=$((PASS+1)); echo "ok $PASS - $1"; }
bad() { FAIL=$((FAIL+1)); echo "FAIL - $1"; }

# 1. -V 版本输出
OUT="$("$PSPG" -V 2>&1)"
if [ "$OUT" = "pspg-5.8.16" ]; then ok "-V 版本输出"; else bad "-V 版本输出: got [$OUT]"; fi

# 2. --about：作者/许可信息，退出码 0
"$PSPG" --about >"$TMP/about.txt" 2>&1
RC=$?
if [ $RC -eq 0 ] && grep -q "is special pager" "$TMP/about.txt" \
   && grep -q "BSD" "$TMP/about.txt"; then
  ok "--about 信息"
else
  bad "--about: rc=$RC"
fi

# 3. --help：用法文本，退出码 0
"$PSPG" --help >"$TMP/help.txt" 2>&1
RC=$?
if [ $RC -eq 0 ] && grep -q "Usage:" "$TMP/help.txt" \
   && grep -q -- "--about" "$TMP/help.txt"; then
  ok "--help 用法"
else
  bad "--help: rc=$RC"
fi

# 4. 未知选项 → 非零退出码并提示 Try --help
"$PSPG" --bogus-option-xyz >/dev/null 2>"$TMP/err.txt"
RC=$?
if [ $RC -ne 0 ] && grep -q "Try" "$TMP/err.txt"; then
  ok "未知选项报错"
else
  bad "未知选项行为: rc=$RC"
fi

# 5. 功能: --csv 非 tty 渲染表格（真实数据管线）
"$PSPG" --csv -f "$HERE/fixtures/sample.csv" >"$TMP/csv.out" 2>&1
RC=$?
if [ $RC -eq 0 ] && grep -q "alice" "$TMP/csv.out" \
   && grep -q "brno" "$TMP/csv.out"; then
  ok "--csv 渲染"
else
  bad "--csv 渲染: rc=$RC, out=$(head -3 "$TMP/csv.out" 2>/dev/null)"
fi

# 6. 功能: --tsv 非 tty 渲染
"$PSPG" --tsv -f "$HERE/fixtures/sample.tsv" >"$TMP/tsv.out" 2>&1
RC=$?
if [ $RC -eq 0 ] && grep -q "prague" "$TMP/tsv.out" \
   && grep -q "bob" "$TMP/tsv.out"; then
  ok "--tsv 渲染"
else
  bad "--tsv 渲染: rc=$RC, out=$(head -3 "$TMP/tsv.out" 2>/dev/null)"
fi

echo "----------------------------------------"
echo "总结: 通过 $PASS / $((PASS+FAIL)), 失败 $FAIL"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
