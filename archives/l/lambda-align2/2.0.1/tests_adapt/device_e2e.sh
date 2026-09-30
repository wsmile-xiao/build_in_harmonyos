#!/bin/sh
# =============================================================================
# DAYU200 真机端到端（规则 12）：lambda2 静态产物在 OpenHarmony 6.0 aarch64 上
# 完成真实工作流 —— 建索引 -> 检索 -> 命中/格式校验（蛋白链路 + 核苷酸链路 + 压缩链路）
# 仅使用设备自带 busybox 工具（sh/grep/cut/wc/gunzip），不依赖 awk/python/curl
# =============================================================================
set -u
cd "$(dirname "$0")" 2>/dev/null || cd .
BIN=./lambda2
PASS=0
FAIL=0
ok()  { PASS=$((PASS + 1)); echo "  [ok $PASS] $1"; }
bad() { FAIL=$((FAIL + 1)); echo "  [FAIL] $1"; }

echo "==================== 设备信息 ===================="
uname -a
echo "OpenHarmony: $(param get const.product.software.version 2>/dev/null)"
echo "==================== 产物信息 ===================="
ls -l "$BIN"
"$BIN" --version && ok "lambda2 --version 可执行" || bad "lambda2 --version 失败"

echo "==================== 蛋白链路 ===================="
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

if "$BIN" mkindexp -d db.fa -i db.fa.lambda --db-index-type fm -t 1 > mkindexp.log 2>&1; then
    ok "mkindexp 建 FM 索引"
else
    cat mkindexp.log; bad "mkindexp 失败"
fi
[ -d db.fa.lambda ] && ok "索引目录 db.fa.lambda 生成" || bad "索引目录缺失"

search_p() {
    "$BIN" searchp -q qry.fa -i db.fa.lambda -a aminoacid -t 1 \
        --version-to-outputfile off -o "$1" > "searchp_$1.log" 2>&1
}

if search_p hits.m8; then ok "searchp 检索（m8）"; else cat "searchp_hits.m8.log"; bad "searchp 失败"; fi
if grep -q "^q1	subj1_hit_target	" hits.m8; then
    ok "m8 命中目标 subj1_hit_target"
else
    bad "m8 未命中 subj1_hit_target"; cat hits.m8
fi
echo "--- m8 命中表 ---"; cat hits.m8

if search_p hits.m9 && grep -q "^# BLASTP " hits.m9; then
    ok "m9 输出含 BLASTP 程序标签"
else
    bad "m9 输出异常"
fi
echo "--- m9 头部 ---"; head -5 hits.m9

if search_p hits.sam && grep -q "^@HD" hits.sam; then
    ok "sam 输出含 @HD 头（$(grep -vc '^@' hits.sam) 条比对记录）"
else
    bad "sam 输出异常"
fi

if search_p hits.m9.gz && gunzip -c hits.m9.gz 2>/dev/null | grep -q "^# BLASTP "; then
    ok "m9.gz 经 zlib 压缩写出并可解压"
else
    bad "m9.gz 链路异常"
fi

if search_p hits.bam; then
    # BAM = BGZF = 多成员 gzip 流。设备自带 busybox gunzip 不支持多成员/BC 子字段
    # （实测报 "bad symbol"），且 busybox 无 od/tr，故用 printf+dd+cmp 断言 BGZF 头部：
    # gzip 魔数 1f 8b、压缩方法 08、标志位含 FEXTRA(04)。
    printf '\037\213\010\004' > bgzf_magic4
    if [ -s hits.bam ] && dd if=hits.bam bs=4 count=1 2>/dev/null | cmp -s - bgzf_magic4; then
        ok "bam 为合法 BGZF（gzip 魔数 1f 8b 08 04 = FEXTRA），$(wc -c < hits.bam) 字节"
    else
        bad "bam 结构异常（非 BGZF）"
    fi
else
    bad "bam 写出失败"
fi

if command -v bzcat >/dev/null 2>&1 || command -v bzip2 >/dev/null 2>&1; then
    if search_p hits.sam.bz2 && { bzcat hits.sam.bz2 2>/dev/null || bzip2 -dc hits.sam.bz2; } | grep -q "^@HD"; then
        ok "sam.bz2 经 bzip2 压缩写出并可解压"
    else
        bad "sam.bz2 链路异常"
    fi
else
    echo "  (skip) 设备无 bzip2/bzcat，跳过 sam.bz2 链路"
fi

echo "==================== 核苷酸链路 ===================="
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

if "$BIN" mkindexn -d dbn.fa -i dbn.fa.lambda --db-index-type fm -t 1 > mkindexn.log 2>&1; then
    ok "mkindexn 建 FM 索引"
else
    cat mkindexn.log; bad "mkindexn 失败"
fi

if "$BIN" searchn -q qn.fa -i dbn.fa.lambda -t 1 --version-to-outputfile off -o hits_nt.m8 > searchn.log 2>&1 \
   && grep -q "^n1	chr1_hit_target	" hits_nt.m8; then
    ok "searchn 命中 chr1_hit_target（$(grep -vc '^$' hits_nt.m8) 条记录）"
else
    cat searchn.log; bad "searchn 未命中"
fi
echo "--- 核苷酸 m8 命中表 ---"; cat hits_nt.m8

echo "==================== 结果 ===================="
echo "device e2e: passed=$PASS failed=$FAIL"
if [ "$FAIL" -eq 0 ]; then
    echo "✅ lambda-align2 DAYU200 真机端到端通过（$PASS 项断言）"
    exit 0
fi
echo "❌ lambda-align2 DAYU200 真机端到端失败（$FAIL 项）"
exit 1
