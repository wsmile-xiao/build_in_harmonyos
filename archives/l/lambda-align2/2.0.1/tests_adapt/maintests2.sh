#!/bin/sh
# =============================================================================
# maintests2.sh —— lambda-align2 2.0.1 上游测试矩阵驱动（2.x CLI 适配版）
#
# 上游 tests/maintests.sh + tests/CMakeLists.txt 是 LAMBDA 1.x 遗留物（tests/ 目录与
# lambda-v1.9.5 逐字节相同；上游 2.x 已在顶层注释掉 add_subdirectory(tests)，Debian 亦禁用）：
#   * 调用 1.x 二进制名 lambda_indexer / lambda（2.x 为单二进制 lambda2 + 子命令）
#   * 使用 1.x 选项 -d/-di/-p（2.x 为 --db-index-type / -i 索引目录 / 子命令 + -a 字母表）
#   * 期望值 `openssl md5 *` 校验 1.x 平铺索引文件（db.fasta.<alph>.sa.sa / binseg_* 等）
#     与输出 md5；2.x 索引是 db.fasta.lambda/ 目录（index.lf.* / index.sa.* / option:* /
#     seq_ids.* / translated_seqs.*），1.x 期望值结构上不可能命中。
#
# 本驱动保持上游测试语义与矩阵不变：
#   * 同一签名：SRCDIR BINDIR PROG DI MODE(MKINDEX|SEARCH) EXTENSION [+ RUN_PREFIX]
#   * 同一测试数据：tests/db_*.fasta.gz、tests/queries_*.fasta.gz
#   * 同一流程：解压数据 -> 建索引 -> 索引校验 -> 比对 -> 检索 -> 输出校验
#   * 同一矩阵：5 PROG x 2 DI x (1 MKINDEX + 7 SEARCH 格式) = 80 例，用例名与上游一致
#
# 三类适配（详见 PR 说明与 notes.md，均有实测证据）：
#   A. 调用行：1.x 命令 -> lambda2 子命令（mkindexn/mkindexp + searchn/searchp）与 2.x 选项
#   B. 期望值：1.x md5sums -> tests_adapt/expected.md5（x86_64 Linux Release 参考构建钉死，
#      OHOS/aarch64 构建逐字节复现）；索引摘要改为「索引目录内相对路径 + md5 排序清单」的摘要
#   C. 上游数据兼容：db_*.fasta 的序列行内嵌空白（1.x 容忍），会触发 2.x
#      detectSeqFileAlphabet() 的严格回环比较而误报 "illegal characters"（该函数用
#      CharString 读入保留空白，而真正建索引的强类型读入会跳过空白），导致 tblastn/tblastx
#      无法建索引。故解压时仅对**序列行**做空白归一（不动标题行、不动任何碱基/氨基酸字符）。
#      该归一被证明对 2.x 无副作用：带空白与去空白数据建出的索引逐文件 md5 完全一致
#      （证据 tests_adapt/whitespace_noop_proof.txt）。
#
# 新增语义断言（不替代上游校验）：BLAST 程序标签（BLASTN/BLASTP/BLASTX/TBLASTN/TBLASTX）、
#   输出非空、格式结构（列数/头部）、压缩格式可解压且魔数正确。
#
# 生成期望值（参考构建）: GEN_EXPECTED=1 GEN_OUT=<file> 运行
# 交叉构建执行目标二进制: 追加 RUN_PREFIX（如 /root/ohpc/bin/ohos-qemu-aarch64）
# =============================================================================
set -u

errorout()
{
    echo "FAIL: $1"
    [ "$MYTMP" = "" ] || rm -rf "${MYTMP}"
    exit 1
}

[ $# -ge 6 ] || { echo "usage: maintests2.sh SRCDIR BINDIR PROG DI MODE EXTENSION [RUN_PREFIX...]"; exit 1; }

SRCDIR=$1
BINDIR=$2
PROG=$3
DI=$4
MODE=$5
EXTENSION=$6
shift 6
RUN="$*"

which md5sum gunzip mktemp cmp diff cat sed find sort xargs > /dev/null 2>&1
[ $? -eq 0 ] || errorout "required tools missing (md5sum gunzip mktemp cmp diff cat sed find sort xargs)"

# ---- 上游 SALPH/QALPHIN/SALPHIN 映射（maintests.sh 第 23-45 行逐行保留）------
SALPH=prot
QALPHIN=prot
SALPHIN=prot
case "$PROG" in "blastn")
    QALPHIN=nucl
    SALPH=nucl
    SALPHIN=nucl
    ;;
"blastp")
    ;;
"blastx")
    QALPHIN=nucl
    ;;
"tblastn")
    SALPH=trans
    SALPHIN=nucl
    ;;
"tblastx")
    SALPH=trans
    QALPHIN=nucl
    SALPHIN=nucl
    ;;
*) errorout "unknown PROG $PROG" ;;
esac

# ---- 2.x CLI 映射 -----------------------------------------------------------
# 上游 1.x: lambda_indexer -d db -di DI -p PROG / lambda -d db -di DI -p PROG -q q -o out
# 2.x     : lambda2 mkindex{p,n} -d db -i db.fasta.lambda --db-index-type DI [-a alph]
#           lambda2 search{p,n} -q q -i db.fasta.lambda [-a alph] -o out
#           （2.x 检索不再接受 --db-index-type：索引类型由索引内 option:db_index_type 决定）
MKCMD=mkindexp
SRCMD=searchp
MKALPH=""
QRYALPH=""
TAG=""
case "$PROG" in "blastn")
    MKCMD=mkindexn
    SRCMD=searchn
    TAG="BLASTN"
    ;;
"blastp")
    MKALPH="-a aminoacid"
    QRYALPH="-a aminoacid"
    TAG="BLASTP"
    ;;
"blastx")
    MKALPH="-a aminoacid"
    QRYALPH="-a dna5"
    TAG="BLASTX"
    ;;
"tblastn")
    MKALPH="-a dna5"
    QRYALPH="-a aminoacid"
    TAG="TBLASTN"
    ;;
"tblastx")
    MKALPH="-a dna5"
    QRYALPH="-a dna5"
    TAG="TBLASTX"
    ;;
esac

MYTMP="$(mktemp -q -d -t "$(basename "$0").XXXXXX" 2>/dev/null || mktemp -q -d)"
[ $? -eq 0 ] || errorout "Could not create tmp"
cd "$MYTMP" || errorout "Could not cd to tmp"

# ---- 数据准备（上游: gunzip < tests/db_${SALPHIN}.fasta.gz > db.fasta）-------
# 适配 C：仅序列行做空白归一；标题行原样保留
gunzip < "${SRCDIR}/tests/db_${SALPHIN}.fasta.gz" | sed '/^>/!s/[ \t]//g' > db.fasta
[ $? -eq 0 ] || errorout "Could not unzip database file"

# ---- 1) 建索引（上游: lambda_indexer -d db.fasta -di DI -p PROG）-------------
${RUN} "${BINDIR}/bin/lambda2" ${MKCMD} -d db.fasta -i db.fasta.lambda --db-index-type ${DI} ${MKALPH} -t 1 > mkindex.log 2>&1
[ $? -eq 0 ] || { cat mkindex.log; errorout "Could not run lambda2 ${MKCMD}"; }
[ -d db.fasta.lambda ] || errorout "index directory not created"

# ---- 2) 索引内容校验（替代上游 1.x 平铺文件 md5，目的相同）------------------
# 注意：上游在 MKINDEX 与 SEARCH 两种模式下都会校验索引（maintests.sh 第 59-71 行），
# 本驱动保持一致；只有 MKINDEX 模式产生/校验 test_mkindex_* 期望值，避免重复条目。
( cd db.fasta.lambda && find . -type f | LC_ALL=C sort | xargs md5sum ) > idx.md5
IDXDIGEST=$(md5sum idx.md5 | cut -d' ' -f1)
IDXNAME="test_mkindex_${PROG}_${DI}"
EXPECTED="${EXPECTED_FILE:-${SRCDIR}/tests_adapt/expected.md5}"

check_index_digest() {
    EXP=$(grep "^${IDXNAME} " "$EXPECTED" | cut -d' ' -f2 | head -1)
    [ -n "$EXP" ] || errorout "no expected value for ${IDXNAME}"
    [ "$EXP" = "$IDXDIGEST" ] || {
        echo "--- 索引内容 md5 明细 ---"; cat idx.md5
        errorout "index digest mismatch for ${IDXNAME}: expected ${EXP} got ${IDXDIGEST}"
    }
}

# ---- INDEXER tests end here（对应上游第 67-71 行同款分支）-------------------
if [ "$MODE" = "MKINDEX" ]; then
    if [ "${GEN_EXPECTED:-0}" = "1" ]; then
        echo "${IDXNAME} ${IDXDIGEST}" >> "${GEN_OUT}"
    else
        check_index_digest
    fi
    rm -rf "${MYTMP}"
    echo "PASS: ${IDXNAME}"
    exit 0
fi

# SEARCH 模式同样校验索引（与上游一致）
[ "${GEN_EXPECTED:-0}" = "1" ] || check_index_digest

# ---- 3) 比对（上游: lambda -d db.fasta -di DI -p PROG -q queries -o output）--
gunzip < "${SRCDIR}/tests/queries_${QALPHIN}.fasta.gz" > queries.fasta
[ $? -eq 0 ] || errorout "Could not unzip queries.fasta"

OUT="output_${PROG}_${DI}.${EXTENSION}"
${RUN} "${BINDIR}/bin/lambda2" ${SRCMD} -q queries.fasta -i db.fasta.lambda ${QRYALPH} -t 1 \
    --version-to-outputfile off -o "${OUT}" > search.log 2>&1
[ $? -eq 0 ] || { cat search.log; errorout "Search failed."; }
[ -s "${OUT}" ] || errorout "output file empty"

# ---- 4) 输出语义断言（新增）------------------------------------------------
case "$EXTENSION" in
m0)
    grep -q "^${TAG} " "${OUT}" || errorout "m0 header does not carry expected BLAST program tag ${TAG}"
    grep -q "Query=" "${OUT}" || errorout "m0 has no Query section"
    grep -q "Score = " "${OUT}" || errorout "m0 has no 'Score = ' line"
    ;;
m8)
    grep -v '^$' "${OUT}" | cut -f12 | grep -q '^$' && errorout "m8 has rows with <12 tab-separated fields"
    ;;
m9)
    grep -q "^# ${TAG} " "${OUT}" || errorout "m9 header does not carry expected BLAST program tag ${TAG}"
    grep -q "^# Query:" "${OUT}" || errorout "m9 has no Query header"
    grep -v '^#' "${OUT}" | grep -v '^$' | cut -f12 | grep -q '^$' && errorout "m9 has data rows with <12 fields"
    ;;
m9.gz)
    gunzip -c "${OUT}" > out.m9.dec 2>/dev/null || errorout "m9.gz cannot be decompressed"
    grep -q "^# ${TAG} " out.m9.dec || errorout "m9.gz payload lacks BLAST tag ${TAG}"
    ;;
sam)
    grep -q "^@HD" "${OUT}" || errorout "sam lacks @HD header"
    grep -v '^@' "${OUT}" | grep -v '^$' | cut -f11 | grep -q '^$' && errorout "sam has rows with <11 fields"
    ;;
sam.bz2)
    (bzcat "${OUT}" 2>/dev/null || bzip2 -dc "${OUT}") > out.sam.dec || errorout "sam.bz2 cannot be decompressed"
    grep -q "^@HD" out.sam.dec || errorout "sam.bz2 payload lacks @HD"
    ;;
bam)
    gunzip -c "${OUT}" > out.bam.dec 2>/dev/null || errorout "bam (BGZF) cannot be decompressed"
    printf 'BAM' > magic3
    head -c 3 out.bam.dec | cmp -s - magic3 || errorout "bam payload lacks BAM magic"
    ;;
esac

# ---- 5) 输出内容校验（替代上游 1.x 输出 md5；压缩格式先解压为规范内容）------
case "$EXTENSION" in
m9.gz)   CANONICAL=$(md5sum out.m9.dec | cut -d' ' -f1) ;;
sam.bz2) CANONICAL=$(md5sum out.sam.dec | cut -d' ' -f1) ;;
bam)     CANONICAL=$(md5sum out.bam.dec | cut -d' ' -f1) ;;
*)       CANONICAL=$(md5sum "${OUT}" | cut -d' ' -f1) ;;
esac

TESTNAME="test_search_${PROG}_${DI}_${EXTENSION}"

if [ "${GEN_EXPECTED:-0}" = "1" ]; then
    echo "${TESTNAME} ${CANONICAL}" >> "${GEN_OUT}"
else
    EXP=$(grep "^${TESTNAME} " "$EXPECTED" | cut -d' ' -f2 | head -1)
    [ -n "$EXP" ] || errorout "no expected value for ${TESTNAME}"
    [ "$EXP" = "$CANONICAL" ] || errorout "output content mismatch for ${TESTNAME}: expected ${EXP} got ${CANONICAL}"
fi

rm -rf "${MYTMP}"
echo "PASS: ${TESTNAME}"
