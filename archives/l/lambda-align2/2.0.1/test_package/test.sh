#!/bin/sh
# =============================================================================
# test_package/test.sh — lambda-align2 消费者端到端用例（规则 12 口径：完整工作流）
#
# 蛋白链路:  lambda2 mkindexp -> searchp -> 校验 m8/m9/sam/m9.gz/bam/sam.bz2 命中与格式
# 核苷酸链路: lambda2 mkindexn -> searchn -> 校验 m8 命中
# 仅用设备可用工具: mktemp/grep/cut/wc/gunzip/cmp/printf（busybox 兼容，无 awk/python）
# LAMBDA2_RUN_PREFIX: 本地 qemu 交叉验证时的执行前缀（设备/CI 为空）
# =============================================================================
set -eu

L2_BIN="$(command -v lambda2)"
RUN="${LAMBDA2_RUN_PREFIX:-}"
N=0
ok()   { N=$((N + 1)); echo "  [ok $N] $1"; }
fail() { echo "  [FAIL] $1"; exit 1; }
l2()   { $RUN "$L2_BIN" "$@"; }

base_dir="${TMPDIR:-.}"
workdir="$(mktemp -d "$base_dir/lambda2-test.XXXXXX" 2>/dev/null || mktemp -d)"
trap 'rm -rf "$workdir"' EXIT
cd "$workdir"

echo "[test] lambda2 --version"
VER_OUT="$(l2 --version 2>&1)"
echo "$VER_OUT" | grep -q "2.0.1" || fail "版本输出不含 2.0.1: $VER_OUT"
ok "lambda2 --version 报告 2.0.1"

# ---------------------------------------------------------------- 蛋白链路
cat > db.fa <<'EOF'
>subj1_hit_target
MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAVQVKVKALPDAQFEVVHSLAKWKR
>subj2_unrelated
GAVLIPFYWSTCMNQDEKRHAGVLIPFYWSTCMNQDEKRHAGVLIPFYWSTCMNQDEKRHAGVLIPFYWSTCMNQDEK
EOF

cat > qry.fa <<'EOF'
>q1
MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAVQVKVKALP
EOF

echo "[test] lambda2 mkindexp (FM 索引)"
l2 mkindexp -d db.fa -i db.fa.lambda --db-index-type fm -t 1 > mkindex.log 2>&1 \
    || { cat mkindex.log; fail "mkindexp 失败"; }
[ -d db.fa.lambda ] || fail "未生成索引目录 db.fa.lambda"
grep -q "^aminoacid$" db.fa.lambda/option:alph_original || fail "索引 option:alph_original 非 aminoacid"
ok "mkindexp 生成 FM 索引（option:alph_original=aminoacid）"

run_search() {  # $1=输出文件
    l2 searchp -q qry.fa -i db.fa.lambda -a aminoacid -t 1 \
        --version-to-outputfile off -o "$1" > "$1.log" 2>&1 || { cat "$1.log"; fail "searchp 失败（$1）"; }
}

echo "[test] lambda2 searchp -> m8"
run_search hits.m8
[ -s hits.m8 ] || fail "m8 输出为空"
grep -v '^$' hits.m8 | cut -f12 | grep -q '^$' && fail "m8 存在字段数 <12 的行"
grep -q "^q1	subj1_hit_target	" hits.m8 || fail "m8 未命中 subj1_hit_target"
ok "m8 命中表：命中 subj1_hit_target 且行字段数 = 12"

echo "[test] lambda2 searchp -> m9"
run_search hits.m9
grep -q "^# BLASTP " hits.m9 || fail "m9 缺少 BLASTP 程序标签"
grep -q "^# Query: q1" hits.m9 || fail "m9 缺少 Query 头"
HITS="$(grep "^# .* hits found" hits.m9 | head -1 | cut -d' ' -f2)"
[ "${HITS:-0}" -ge 1 ] 2>/dev/null || fail "m9 报告命中数异常: ${HITS:-<空>}"
ok "m9 带 BLASTP 标签/Query 头，报告 ${HITS} 条命中"

echo "[test] lambda2 searchp -> sam"
run_search hits.sam
grep -q "^@HD" hits.sam || fail "sam 缺少 @HD 头"
grep -v '^@' hits.sam | grep -v '^$' | cut -f11 | grep -q '^$' && fail "sam 存在字段数 <11 的行"
SAM_HITS="$(grep -vc '^@' hits.sam)"
[ "$SAM_HITS" -ge 1 ] || fail "sam 无命中记录"
ok "sam 含 @HD 头与 ${SAM_HITS} 条记录（字段数 ≥11）"

echo "[test] lambda2 searchp -> m9.gz（zlib 链路）"
run_search hits.m9.gz
gunzip -c hits.m9.gz > hits.m9.dec 2>/dev/null || fail "m9.gz 无法解压（zlib 写链路异常）"
cmp -s hits.m9.dec hits.m9 || fail "m9.gz 解压内容与 m9 不一致"
ok "m9.gz 可解压且与明文 m9 逐字节一致"

echo "[test] lambda2 searchp -> bam（BGZF/zlib 链路）"
run_search hits.bam
gunzip -c hits.bam > hits.bam.dec 2>/dev/null || fail "bam(BGZF) 无法解压"
printf 'BAM' > magic3
head -c 3 hits.bam.dec | cmp -s - magic3 || fail "bam 解压后缺少 BAM\\1 魔数"
ok "bam 为合法 BGZF 且解压后带 BAM 魔数"

if command -v bzcat > /dev/null 2>&1 || command -v bzip2 > /dev/null 2>&1; then
    echo "[test] lambda2 searchp -> sam.bz2（bzip2 链路）"
    run_search hits.sam.bz2
    (bzcat hits.sam.bz2 2>/dev/null || bzip2 -dc hits.sam.bz2) > hits.sam.dec \
        || fail "sam.bz2 无法解压（bzip2 写链路异常）"
    grep -q "^@HD" hits.sam.dec || fail "sam.bz2 解压后缺少 @HD 头"
    cmp -s hits.sam.dec hits.sam || fail "sam.bz2 解压内容与 sam 不一致"
    ok "sam.bz2 可解压且与明文 sam 逐字节一致"
else
    echo "  [skip] 环境无 bzip2/bzcat，跳过 sam.bz2 链路"
fi

# -------------------------------------------------------------- 核苷酸链路
cat > dbn.fa <<'EOF'
>chr1_hit_target
ACGTACGTACGTACGTTTGGCCAATTGGCCAATTGGCCAATTGGCCAATTGGCCAATTGGCCAATTGGCCAA
>chr2_unrelated
TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT
EOF

cat > qn.fa <<'EOF'
>n1
TTGGCCAATTGGCCAATTGGCCAATTGGCCAA
EOF

echo "[test] lambda2 mkindexn + searchn（核苷酸链路）"
l2 mkindexn -d dbn.fa -i dbn.fa.lambda --db-index-type fm -t 1 > mkindexn.log 2>&1 \
    || { cat mkindexn.log; fail "mkindexn 失败"; }
grep -q "^dna5$" dbn.fa.lambda/option:alph_original || fail "核苷酸索引 option:alph_original 非 dna5"
ok "mkindexn 生成 FM 索引（option:alph_original=dna5）"

l2 searchn -q qn.fa -i dbn.fa.lambda -t 1 --version-to-outputfile off -o hits_nt.m8 > searchn.log 2>&1 \
    || { cat searchn.log; fail "searchn 失败"; }
grep -q "^n1	chr1_hit_target	" hits_nt.m8 || fail "searchn 未命中 chr1_hit_target"
NT_HITS="$(grep -vc '^$' hits_nt.m8)"
ok "searchn 命中 chr1_hit_target（${NT_HITS} 条记录）"

echo "✅ lambda-align2 消费者端到端用例通过：${N} 项断言（蛋白 m8/m9/sam/m9.gz/bam[+sam.bz2] + 核苷酸 m8）"
echo "tests passed: ${N}/${N} (lambda-align2 consumer end-to-end)"
