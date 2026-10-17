#!/bin/sh
# test_package/test.sh — lie 2.2.2 消费者冒烟（POSIX sh，经 conanrun PATH 执行 bin/lie）
#
# PAGER=cat：上游 printexpr 走 tmpnam+fopen 分页路径——/tmp 可写环境 fopen 成功时
# 输出先进临时文件再交给 $PAGER（默认 less，设备/CI 均可能不存在 → 输出丢失、断言假失败）；
# /tmp 只读(EROFS) 环境 fopen 失败由 0001 补丁回退 stdout。两种环境统一用 cat 兜底，
# 保证断言只考「本包交付了什么」，不考分页器是否安装。
PAGER=cat
export PAGER
set -u

fail=0
n=0

ok() { n=$((n + 1)); echo "[ok]   $1"; }
no() { n=$((n + 1)); fail=1; echo "[FAIL] $1"; }

# ①② 算术核心（ pocket-calculator 路径，纯二进制不依赖 INFO 数据）
out=$(printf '2+3;\n' | lie 2>&1); rc=$?
[ "$rc" -eq 0 ] && ok "arithmetic '2+3;' exit 0" || no "arithmetic exit rc=$rc (期望 0)"
echo "$out" | grep -q '^[[:space:]]*5[[:space:]]*$' \
    && ok "arithmetic '2+3' evaluates to 5" \
    || no "arithmetic value, 输出=$(echo "$out" | tr '\n' '|')"

# ③④ ?help —— 走 printexpr（0001 补丁面：/tmp EROFS 下修前 rc=139、修后 rc=0）
#        且断言帮助正文来自已安装的 INFO 数据文件
out=$(printf '?help\n' | lie 2>&1); rc=$?
[ "$rc" -eq 0 ] && ok "?help exit 0 (printexpr NULL 补丁面)" || no "?help rc=$rc (期望 0，修前 139)"
echo "$out" | grep -q 'Other useful help available' \
    && ok "?help 输出含 INFO 帮助数据" \
    || no "?help 输出缺 INFO 数据, 头 80 字=$(echo "$out" | head -c 80 | tr '\n' ' ')"

# ⑤⑥ ?dim —— printdocument 按 seq 读 INFO.<n> 文档体（验证数据文件随包交付且可随机定位）
out=$(printf '?dim\n' | lie 2>&1); rc=$?
[ "$rc" -eq 0 ] && ok "?dim exit 0" || no "?dim rc=$rc (期望 0)"
echo "$out" | grep -q 'dimension of the Lie group' \
    && ok "?dim 输出含 INFO.0-4 文档正文" \
    || no "?dim 输出缺文档正文, 头 80 字=$(echo "$out" | head -c 80 | tr '\n' ' ')"

# ⑦ 干净退出（EOF 路径 rc=0，包装脚本 exec 链可透传）
printf '' | lie >/dev/null 2>&1; rc=$?
[ "$rc" -eq 0 ] && ok "empty input exit 0" || no "empty input rc=$rc (期望 0)"

echo "test_package: $n/$n assertions, fail=$fail"
[ "$fail" -eq 0 ] || exit 1
exit 0
