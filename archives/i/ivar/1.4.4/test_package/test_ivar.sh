#!/bin/bash
# 消费者测试 — ivar 1.4.4
# 用法: test_ivar.sh <包内 ivar 绝对路径>
# 7 项断言，全部离线，真实执行被适配工具（R34）。
# 上游 21 项单元测试由构建阶段 make check 运行（见 MANIFEST.yml）。
set -u
IVAR="$1"
HERE="$(cd "$(dirname "$0")" && pwd)"
TMP="$(mktemp -d)" || exit 1
trap 'rm -rf "$TMP"' EXIT
PASS=0
FAIL=0

ok() { PASS=$((PASS+1)); echo "ok $PASS - $1"; }
bad() { FAIL=$((FAIL+1)); echo "FAIL - $1"; }

# 1. version 子命令首行
OUT="$("$IVAR" version 2>&1 | head -1)"
if [ "$OUT" = "iVar version 1.4.4" ]; then ok "ivar version 首行"; else bad "ivar version 首行: got [$OUT]"; fi

# 2. -v 短选项同输出
OUT="$("$IVAR" -v 2>&1 | head -1)"
if [ "$OUT" = "iVar version 1.4.4" ]; then ok "ivar -v 短选项"; else bad "ivar -v 短选项: got [$OUT]"; fi

# 3. 无参数 → 打印 Usage 且退出码非 0（main 返回 -1）
"$IVAR" >"$TMP/usage.txt" 2>&1
RC=$?
if [ $RC -ne 0 ] && grep -q "^Usage:" "$TMP/usage.txt"; then
  ok "无参数: Usage 提示 + 非零退出码"
else
  bad "无参数行为: rc=$RC"
fi

# 4. 未知命令 → "Unknown command" 提示
"$IVAR" boguscmd >"$TMP/unk.txt" 2>&1
if grep -q 'Unknown command: "boguscmd"' "$TMP/unk.txt"; then
  ok "未知命令提示"
else
  bad "未知命令提示"
fi

# 5. consensus -h → 帮助文本，退出码 0
"$IVAR" consensus -h >"$TMP/ch.txt" 2>&1
RC=$?
if [ $RC -eq 0 ] && grep -q -- "-i" "$TMP/ch.txt"; then
  ok "consensus -h 帮助"
else
  bad "consensus -h: rc=$RC"
fi

# 6. trim 缺必需参数 → 非零退出码
#    上游 trim 缺 -i 时回退读 stdin（help 原文 "If not specified will use
#    standard in"）：buildbot/CI 的 stdin 是永不关闭的管道，裸调用会永久
#    阻塞在 sam_hdr_read（CI 4×14400s 无输出超时实证）；显式 </dev/null
#    令 sam_hdr_read 立即失败（trim_primer_quality.cpp:595-598 "Unable
#    to read header from input file"）→ rc≠0，断言语义在任意环境确定。
"$IVAR" trim </dev/null >/dev/null 2>&1
RC=$?
if [ $RC -ne 0 ]; then ok "trim 缺参非零退出"; else bad "trim 缺参退出码: rc=$RC"; fi

# 7. 功能: consensus 子命令从 mpileup 真实生成共识序列（fixtures/10 位置全 A，
#    depth 3、质量 III=Q40）。ivar consensus 的 mpileup 输入走 stdin（ivar.cpp
#    isatty 检查强制管道），-i 是 FASTA 头 seq_id 不是输入文件；产物为
#    <prefix>.fa + <prefix>.qual.txt（call_consensus_pileup.cpp:166-167），
#    无 -i 时头为 >Consensus_<prefix 基名>_threshold_<t>_quality_<q>。
#    -m 1：默认 -m 10 会把 depth 3 的全部位置滤成 gap。
"$IVAR" consensus -p "$TMP/cns" -q 20 -m 1 \
  < "$HERE/fixtures/sample.mpileup" >"$TMP/cns.log" 2>&1
RC=$?
if [ $RC -eq 0 ] && [ -s "$TMP/cns.fa" ] \
   && grep -q "^>Consensus_" "$TMP/cns.fa" \
   && grep -q "^AAAAAAAAAA$" "$TMP/cns.fa" \
   && [ -s "$TMP/cns.qual.txt" ]; then
  ok "consensus 功能调用生成共识序列"
else
  bad "consensus 功能调用: rc=$RC, log=$(cat "$TMP/cns.log" 2>/dev/null | head -3)"
fi

echo "----------------------------------------"
echo "总结: 通过 $PASS / $((PASS+FAIL)), 失败 $FAIL"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
