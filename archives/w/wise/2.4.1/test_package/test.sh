#!/data/service/hnp/bin/bash
# test_package/test.sh — wise 2.4.1 鸿蒙特有测试（消费者侧完整端到端用例）
#
# 在 conanrun 运行环境中执行：PATH 含包安装的 bin/，且包通过 runenv_info
# 导出了 WISECONFIGDIR（指向 share/wise/wisecfg）。
#
# 本脚本是**消费者用例**而非断言集合：每个用例都是一条完整的端到端流程
#   「由消费者构造输入 → 真实执行包内安装的程序 → 程序读取包导出的
#      WISECONFIGDIR 运行期数据 → 产出真实比对结果 → 校验结果内容」，
#   任一步骤失败即该用例 FAIL，最终以「通过用例数 / 用例总数」为结果。
#
# 用例清单（7 个）：
#   HC-1 消费链路入口：11 个程序经 PATH 可定位，包导出 WISECONFIGDIR 且
#        4 个关键运行期数据可读，11 个程序 -version 均报告 wise2-4-1
#   HC-2 genewise    蛋白 × 基因组 DNA 比对（加载 BLOSUM62.bla/codon.table/gene.stat）
#   HC-3 estwise     蛋白 × cDNA 比对
#   HC-4 dnal        DNA × DNA 局部比对（自比对，确定性 Score 2065）
#   HC-5 psw         蛋白 × 蛋白 Smith-Waterman 比对
#   HC-6 dba         DNA × DNA DBA 块比对（自比对，100% 覆盖 MATCH_D）
#   HC-7 promoterwise 双 DNA 启动子预测（完整 BLAST 格式报告 + 比对区段）
set -uo pipefail

# 注释: 不使用 /tmp（OHOS /tmp 只读），就地使用当前可写目录
WORK="$(pwd)/wise-test-run-$$"
mkdir -p "$WORK"
trap 'rm -rf "$WORK"' EXIT
cd "$WORK"

PASS=0
FAIL=0

hdr() { echo; echo "[case] $*"; }
ok()  { echo "  ✅ $*"; }
bad() { echo "  ❌ $*"; }
finish_case() {
  if [ "$1" -eq 0 ]; then
    PASS=$((PASS + 1)); echo "  → PASS"
  else
    FAIL=$((FAIL + 1)); echo "  → FAIL"
  fi
}

PROGS="genewise estwise genewisedb estwisedb dnal psw pswdb dba promoterwise scanwise scanwise_server"

# ---------------------------------------------------------------- 测试数据
# 取自上游 src/test，序列很短以保证整个 test_package 秒级完成
cat > short.pep <<'EOF'
>roa1_drome
VEPKRAVPRQDIDSPNAGATVKKLFVGALKDDHDEQSIRDYFQHFGNIVD
INIVIDKETGKKRGFAFVEFDDYDPVDKVVLQKQHQLNGKMVDVKKALPK
QNDQQGGGGGRGGPGGRAGGNRGNMGGGNYGNQNGGGNWNNGGNNWGNNR
EOF

cat > short.dna <<'EOF'
>HSHNCPA1
CACTTAACTGTGAAAGATATTTGTTGGTGGCATTAAAGAAGACACTGAAGAACATCAC
CTAAGAGATTATTTTGAACAGTATGGAAAAATTGAAGTGATTGAAATCATGACTGACCGA
GGCAGTGGCAAGAAAAGGGGCTTTGCCTTRGTAACCTTTGACGACCATGACTCCGTGGAT
AAGATTGTCATTCAGAAATACCATACTGTGAATGGCCACAACTGTGAAGTTAGAAAAGCC
CTGTCAAAGCAAGAGATGGCTAGTGCTTCATCCAGCCAAAGAGGTCGAAGTGGTTCTGGA
AACTTTGGTGGTGGTCGTGGAGGTGGTTTCGGTGGGAATGACAACTTCGGTCGTGGAGGA
AACTTCAGTGGTCGTGGTYGCTTTGGTGGCAGCCGTGGTGGTGGTGGATATGGTGGC
EOF

cat > road.pep <<'EOF'
>roa1_drome
MVNSNQNQNGNSNGHDDDFPQDSITEPEHMRKLFIGGLDYRTTDENLKAH
FEKWGNIVDVVVMKDPRTKRSRGFGFITYSHSSMIDEAQKSRPHKIDGRV
VEPKRAVPRQDIDSPNAGATVKKLFVGALKDDHDEQSIRDYFQHFGNIVD
INIVIDKETGKKRGFAFVEFDDYDPVDKVVLQKQHQLNGKMVDVKKALPK
QNDQQGGGGGRGGPGGRAGGNRGNMGGGNYGNQNGGGNWNNGGNNWGNNR
GGNDNWGNNSFGGGGGGGGGYGGGNNSWGNNNPWDNGNGGGNFGGGGNNW
NNGGNDFGGYQQNYGGGPQRGGGNFNNNRMQPYQGGGGFKAGGGNQGNYG
GNNQGFNNGGNNRRY
EOF

# ================================================================ HC-1
hdr "HC-1 消费链路入口（PATH 定位 + 包导出运行期数据 + 版本一致性）"
rc=0
for p in $PROGS; do
  command -v "$p" >/dev/null 2>&1 || { bad "$p 不在 PATH 中"; rc=1; }
done
[ $rc -eq 0 ] && ok "11 个命令行程序全部就位"

[ -n "${WISECONFIGDIR:-}" ] || { bad "WISECONFIGDIR 未由包导出"; rc=1; }
if [ -n "${WISECONFIGDIR:-}" ]; then
  for f in BLOSUM62.bla codon.table gene.stat human.gf; do
    [ -f "$WISECONFIGDIR/$f" ] || { bad "缺少运行期数据 $WISECONFIGDIR/$f"; rc=1; }
  done
  [ $rc -eq 0 ] && ok "WISECONFIGDIR=$WISECONFIGDIR（BLOSUM62.bla / codon.table / gene.stat / human.gf 齐全）"
fi

# wise2 的工具在打印版本/用法后以非 0 码退出（genewise/dnal 等为 63，dba 为 255，
# promoterwise 为 12），这是上游既有行为，故只校验输出内容。
for p in $PROGS; do
  out="$("$p" -version 2>&1 || true)"
  case "$out" in
    *wise2-4-1*) ;;
    *) bad "$p -version 未报告 wise2-4-1: $out"; rc=1 ;;
  esac
done
[ $rc -eq 0 ] && ok "11 个程序 -version 均报告 wise2-4-1"
finish_case $rc

# ================================================================ HC-2
hdr "HC-2 genewise 端到端：蛋白 × 基因组 DNA 比对"
rc=0
genewise -quiet short.pep short.dna > gw.out 2> gw.err \
  || { bad "genewise 退出码非 0"; cat gw.err; rc=1; }
if [ -s gw.out ]; then
  grep -q 'roa1_drome' gw.out || { bad "缺少 query 名 roa1_drome"; rc=1; }
  grep -q 'HSHNCPA1'   gw.out || { bad "缺少 target 名 HSHNCPA1"; rc=1; }
  grep -qE 'Comp Matrix:[[:space:]]+BLOSUM62\.bla' gw.out \
    || { bad "未加载 BLOSUM62.bla"; rc=1; }
  grep -qE 'Codon Table:[[:space:]]+codon\.table' gw.out \
    || { bad "未加载 codon.table"; rc=1; }
  grep -qE 'Gene Parameter file:[[:space:]]+gene\.stat' gw.out \
    || { bad "未加载 gene.stat"; rc=1; }
  grep -q 'DYDPVDKVVLQKQHQLNGK' gw.out \
    || { bad "比对结果中缺少 rrm 保守肽段"; rc=1; }
  grep -qx '//' gw.out || { bad "输出缺少结束标记 //"; rc=1; }
  [ $rc -eq 0 ] && ok "产出完整比对结果（保守肽段 + BLOSUM62/codon.table/gene.stat 均加载）"
else
  bad "genewise 无输出"; rc=1
fi
finish_case $rc

# ================================================================ HC-3
hdr "HC-3 estwise 端到端：蛋白 × cDNA 比对"
rc=0
estwise -quiet short.pep short.dna > ew.out 2> ew.err \
  || { bad "estwise 退出码非 0"; cat ew.err; rc=1; }
if [ -s ew.out ]; then
  grep -q 'roa1_drome'          ew.out || { bad "缺少 query 名"; rc=1; }
  grep -q 'DYDPVDKVVLQKQHQLNGK' ew.out || { bad "比对结果中缺少保守肽段"; rc=1; }
  grep -qx '//' ew.out || { bad "输出缺少结束标记 //"; rc=1; }
  [ $rc -eq 0 ] && ok "产出完整比对结果"
else
  bad "estwise 无输出"; rc=1
fi
finish_case $rc

# ================================================================ HC-4
hdr "HC-4 dnal 端到端：DNA × DNA 局部比对（自比对）"
rc=0
dnal -quiet short.dna short.dna > dn.out 2> dn.err \
  || { bad "dnal 退出码非 0"; cat dn.err; rc=1; }
if [ -s dn.out ]; then
  grep -q '^Score 2065$' dn.out \
    || { bad "自比对得分非预期 2065：$(head -n1 dn.out)"; rc=1; }
  grep -q 'HSHNCPA1' dn.out || { bad "缺少序列名 HSHNCPA1"; rc=1; }
  [ $rc -eq 0 ] && ok "自比对得分 2065（与上游 test/basic_cdna 基线一致）"
else
  bad "dnal 无输出"; rc=1
fi
finish_case $rc

# ================================================================ HC-5
hdr "HC-5 psw 端到端：蛋白 × 蛋白 Smith-Waterman 比对"
rc=0
psw -quiet road.pep short.pep > pw.out 2> pw.err \
  || { bad "psw 退出码非 0"; cat pw.err; rc=1; }
if [ -s pw.out ]; then
  grep -q 'roa1_drome' pw.out || { bad "缺少序列名 roa1_drome"; rc=1; }
  grep -q 'VEPKRAVPRQDIDSPNAGATVKKLFVGALKDDHDEQSIRDYFQHFGNIV' pw.out \
    || { bad "比对结果中缺少 rrm 保守肽段"; rc=1; }
  grep -qx '//' pw.out || { bad "输出缺少结束标记 //"; rc=1; }
  [ $rc -eq 0 ] && ok "产出完整比对结果"
else
  bad "psw 无输出"; rc=1
fi
finish_case $rc

# ================================================================ HC-6
hdr "HC-6 dba 端到端：DNA × DNA DBA 块比对（自比对）"
rc=0
dba -quiet short.dna short.dna > db.out 2> db.err \
  || { bad "dba 退出码非 0"; cat db.err; rc=1; }
if [ -s db.out ]; then
  grep -qE '^score = [0-9]+\.[0-9]+$' db.out \
    || { bad "缺少 score 行：$(head -n2 db.out)"; rc=1; }
  grep -q '100%'    db.out || { bad "自比对未达到 100% 覆盖"; rc=1; }
  grep -q 'MATCH_D' db.out || { bad "自比对未判为 MATCH_D"; rc=1; }
  [ $rc -eq 0 ] && ok "$(grep -E '^score = ' db.out)（100% 覆盖，MATCH_D）"
else
  bad "dba 无输出"; rc=1
fi
finish_case $rc

# ================================================================ HC-7
hdr "HC-7 promoterwise 端到端：双 DNA 启动子预测（BLAST 格式报告）"
rc=0
promoterwise -quiet short.dna short.dna > pm.out 2> pm.err \
  || { bad "promoterwise 退出码非 0"; cat pm.err; rc=1; }
if [ -s pm.out ]; then
  grep -q 'Search\.\.*done' pm.out || { bad "未走完搜索阶段（缺少 Search...done）"; rc=1; }
  grep -q 'HSHNCPA1'        pm.out || { bad "报告中缺少命中序列 HSHNCPA1"; rc=1; }
  grep -qE 'Length = 415'   pm.out \
    || { bad "命中序列长度非 415（415 为 short.dna 真实长度）"; rc=1; }
  grep -q 'Sbjct:'          pm.out || { bad "报告中缺少 Sbjct 比对区段"; rc=1; }
  [ $rc -eq 0 ] && ok "产出完整报告（Search done + 命中 HSHNCPA1 + 比对区段）"
else
  bad "promoterwise 无输出"; rc=1
fi
finish_case $rc

# ---------------------------------------------------------------- 汇总
echo
echo "================ 用例汇总 ================"
echo "通过: $PASS / $((PASS + FAIL))"
if [ "$FAIL" -ne 0 ]; then
  echo "❌❌ 有 $FAIL 个用例失败"
  exit 1
fi
echo "✅✅ wise 2.4.1 鸿蒙特有测试全部通过（7 个完整端到端消费者用例）"
