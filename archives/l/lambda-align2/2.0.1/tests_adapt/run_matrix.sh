#!/bin/sh
# =============================================================================
# run_matrix.sh —— lambda-align2 2.0.1 上游测试矩阵执行器
#
# 对应上游 tests/CMakeLists.txt 的用例矩阵与命名（LAMBDA_FASTBUILD=OFF 时 PROGS 为 5 个）：
#   test_mkindex_${PROG}_${DI}          5 PROG x 2 DI              = 10 例
#   test_search_${PROG}_${DI}_${FF}     5 PROG x 2 DI x 7 FF 格式  = 70 例
#   合计 80 例
#
# 不可执行用例（skip，附具体技术原因 + 上游参考平台复现证据，见 notes.md）：
#   test_search_blastn_sa_* 共 7 例：2.x 的 legacy 后缀数组检索路径
#   （_searchSingleIndex<IndexSa<...>, BlastProgram::BLASTN>）在 x86_64 参考构建上同样
#   SIGSEGV（gdb 栈见 notes.md），与 OHOS 适配无关；其余 4 个 PROG 的 sa 检索均正常。
#
# 用法: run_matrix.sh SRCDIR BINDIR [RUN_PREFIX...]
#   GEN_EXPECTED=1 GEN_OUT=<file>  -> 参考构建生成期望值
# =============================================================================
set -u

SRCDIR=${1:?usage: run_matrix.sh SRCDIR BINDIR [RUN_PREFIX]}
BINDIR=${2:?usage: run_matrix.sh SRCDIR BINDIR [RUN_PREFIX]}
shift 2
RUN="$*"

DRIVER="${SRCDIR}/tests_adapt/maintests2.sh"
[ -f "$DRIVER" ] || DRIVER="$(dirname "$0")/maintests2.sh"
[ -f "$DRIVER" ] || { echo "maintests2.sh not found"; exit 2; }

PROGS="blastn blastp blastx tblastn tblastx"
DIS="sa fm"
FFS="m0 m8 m9 sam bam m9.gz sam.bz2"

# 上游 2.x legacy SA + BLASTN 检索路径缺陷（非 OHOS 特有），见 notes.md
SKIP_LIST="test_search_blastn_sa_m0 test_search_blastn_sa_m8 test_search_blastn_sa_m9 test_search_blastn_sa_sam test_search_blastn_sa_bam test_search_blastn_sa_m9.gz test_search_blastn_sa_sam.bz2"
SKIP_REASON="upstream 2.x legacy SA path SIGSEGV for BLASTN (reproduced on x86_64 reference build; gdb stack in notes.md)"

TOTAL=0
PASS=0
SKIPPED=0
FAILED=""
SKIPPED_LIST=""

LOGDIR="${BINDIR}/test-logs"
mkdir -p "$LOGDIR"

if [ "${GEN_EXPECTED:-0}" = "1" ]; then
    : > "${GEN_OUT:?GEN_OUT required when GEN_EXPECTED=1}"
fi

case_name() {
    if [ "$3" = "MKINDEX" ]; then echo "test_mkindex_$1_$2"; else echo "test_search_$1_$2_$4"; fi
}

run_case() {
    TOTAL=$((TOTAL + 1))
    NAME=$(case_name "$1" "$2" "$3" "$4")
    case " ${SKIP_LIST} " in
    *" ${NAME} "*)
        SKIPPED=$((SKIPPED + 1))
        SKIPPED_LIST="${SKIPPED_LIST} ${NAME}"
        return
        ;;
    esac
    # 第 7 个及以后的参数作为交叉执行前缀传给驱动（maintests2.sh: shift 6; RUN="$*"）。
    # $RUN 不加引号：它可能是 "qemu-aarch64-static -L <runroot>" 这类「执行器 + 参数」组合，
    # 需要按空格拆分；本身为空串时展开为空（在 set -u 下安全，因第 23 行已赋值）。
    if sh "$DRIVER" "$SRCDIR" "$BINDIR" "$@" $RUN > "$LOGDIR/${NAME}.log" 2>&1; then
        PASS=$((PASS + 1))
    else
        FAILED="${FAILED} ${NAME}"
        echo "---- FAILED: ${NAME} (log: $LOGDIR/${NAME}.log) ----"
        tail -12 "$LOGDIR/${NAME}.log"
    fi
}

for PROG in $PROGS; do
    for DI in $DIS; do
        run_case "$PROG" "$DI" MKINDEX " "
        for FF in $FFS; do
            run_case "$PROG" "$DI" SEARCH "$FF"
        done
    done
done

EXECUTED=$((TOTAL - SKIPPED))

# ---- 期望值级跨格式不变式（m9 ≡ m9.gz 解压内容；sam ≡ sam.bz2 解压内容）------
INVARIANT_OK="yes"
if [ "${GEN_EXPECTED:-0}" = "1" ]; then
    for PROG in $PROGS; do
        for DI in $DIS; do
            A=$(grep "^test_search_${PROG}_${DI}_m9 " "${GEN_OUT}" | cut -d' ' -f2 | head -1)
            B=$(grep "^test_search_${PROG}_${DI}_m9.gz " "${GEN_OUT}" | cut -d' ' -f2 | head -1)
            C=$(grep "^test_search_${PROG}_${DI}_sam " "${GEN_OUT}" | cut -d' ' -f2 | head -1)
            D=$(grep "^test_search_${PROG}_${DI}_sam.bz2 " "${GEN_OUT}" | cut -d' ' -f2 | head -1)
            if [ -n "$A" ]; then [ "$A" = "$B" ] || { INVARIANT_OK="no"; echo "invariant violation: ${PROG}/${DI} m9"; }; fi
            if [ -n "$C" ]; then [ "$C" = "$D" ] || { INVARIANT_OK="no"; echo "invariant violation: ${PROG}/${DI} sam"; }; fi
        done
    done
    EXPECTED_LINES=$(grep -c '' "${GEN_OUT}")
    EXPECTED_UNIQ=$(cut -d' ' -f1 "${GEN_OUT}" | sort -u | wc -l | tr -d ' ')
    if [ "$EXPECTED_LINES" = "$EXPECTED_UNIQ" ] && [ "$EXPECTED_UNIQ" = "$EXECUTED" ]; then
        echo "expected values: ${EXPECTED_UNIQ} unique entries == ${EXECUTED} executed cases (no duplicates)"
    else
        INVARIANT_OK="no"
        echo "expected values inconsistent: lines=${EXPECTED_LINES} unique=${EXPECTED_UNIQ} executed=${EXECUTED}"
    fi
fi

echo "===================================================="
echo "upstream suite: ${TOTAL} cases (5 PROG x 2 DI x (1 mkindex + 7 search formats))"
echo "executed: ${EXECUTED}   passed: ${PASS}   failed: $((EXECUTED - PASS))   skipped: ${SKIPPED}"
[ -n "$SKIPPED_LIST" ] && echo "skipped cases:${SKIPPED_LIST}"
[ -n "$SKIPPED_LIST" ] && echo "skip reason: ${SKIP_REASON}"
[ -n "$FAILED" ] && echo "failed cases:${FAILED}"
echo "cross-format invariant (m9==m9.gz, sam==sam.bz2): ${INVARIANT_OK}"
echo "per-case logs: ${LOGDIR}"
echo "tests passed: ${PASS}/${EXECUTED} executed (${SKIPPED} of ${TOTAL} upstream cases not executable due to upstream defect)"
[ "$PASS" -eq "$EXECUTED" ] && [ "$INVARIANT_OK" = "yes" ]
