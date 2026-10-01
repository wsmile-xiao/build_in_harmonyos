#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# test_package/test.sh — piler2 功能回归套件
#
# 背景：上游 PILER tarball 不含任何自动化测试（无 tests/、无 check/test 目标、
#       无 ctest/pytest），也不提供样例数据。本套件按上游 User Guide 记载的
#       全部命令行工作流补全，覆盖 main.cpp 分派的全部子命令
#       （-trs / -trs2fasta / -tr / -tan / -tanmotif2fasta / -cons /
#         -annot / -annotedge / -crisp / -help / -version）共 13 项，
#       并补充上游可选行为修饰 flag 的 3 项用例
#       （-multihit / -quiet / -exact），合计 16 项。
#       上游另有 -edge / -pilesonly 两个 flag 声明于 options.cpp 的 FLAG_OPT
#       表，但全工程无任何引用（死选项），无可测行为，故不设用例。
#
# 用法: test.sh <data-dir> <out-dir>
# 退出码: 0 = 全部通过；1 = 存在失败用例
# 依赖: bash + grep + awk + wc + cmp（OHOS 自带基础工具）+ 被测二进制 piler2
# 每用例原始输出: <out-dir>/<case>.log，退出码: <out-dir>/<case>.rc
# 注: 仅 `set -u`（不加 -e/-o pipefail）—— 测试运行器必须在单个用例失败后继续跑完
#     其余用例以产出完整统计，失败与否由 <case>.rc 与末尾 FAIL 计数判定。
# ─────────────────────────────────────────────────────────────────────────────
set -u

DATA="${1:?usage: test.sh <data-dir> <out-dir>}"
OUT="${2:?usage: test.sh <data-dir> <out-dir>}"
BIN="${PILER_BIN:-piler2}"
mkdir -p "$OUT"

PASS=0; FAIL=0; SKIP=0
SUMMARY="$OUT/SUMMARY.tsv"
: > "$SUMMARY"

_record() {  # _record <case> <PASS|FAIL|SKIP> <detail>
    printf '%s\t%s\t%s\n' "$1" "$2" "$3" >> "$SUMMARY"
    case "$2" in
        PASS) PASS=$((PASS + 1)) ;;
        FAIL) FAIL=$((FAIL + 1)) ;;
        *)    SKIP=$((SKIP + 1)) ;;
    esac
    printf '%-4s %-20s %s\n' "$2" "$1" "$3"
}

# run <case> <args...> —— 执行子命令，记录合并输出（<case>.log）与退出码（<case>.rc）
run() {
    local c="$1"; shift
    "$BIN" "$@" >"$OUT/$c.log" 2>&1
    local rc=$?
    printf '%s\n' "$rc" > "$OUT/$c.rc"
    return 0
}
rc_of() { cat "$OUT/$1.rc"; }
# 取 GFF 行中 Annot "<picture> ..." 的 20 字符图示；打印所有长度异常的行
pics_badlen() {  # pics_badlen <file>
    awk -F'Annot "' 'NF>1{split($2,x,"\""); split(x[1],y," "); if (length(y[1])!=20) print FILENAME":"NR}' "$1" 2>/dev/null | wc -l | tr -d ' '
}

echo "=== piler2 functional suite: data=$DATA out=$OUT binary=$(command -v "$BIN" || echo "$BIN") ==="

# ── 1. -version ──────────────────────────────────────────────────────────────
run version -version
r=$(rc_of version)
if [ "$r" = 0 ] && grep -q "PILER v1.0" "$OUT/version.log"; then
    _record version PASS "rc=0, banner 'PILER v1.0'"
else
    _record version FAIL "rc=$r, expected rc=0 and banner 'PILER v1.0'"
fi

# ── 2. -help（必须列出上游手册记载的子命令）─────────────────────────────────
run help -help
r=$(rc_of help)
missing=""
for sub in "-trs" "-trs2fasta" "-cons" "-annot" "-help" "-version"; do
    grep -q -- "$sub" "$OUT/help.log" || missing="$missing $sub"
done
if [ "$r" = 0 ] && [ -z "$missing" ]; then
    _record help PASS "rc=0, usage lists -trs/-trs2fasta/-cons/-annot/-help/-version"
else
    _record help FAIL "rc=$r, missing usage entries:$missing"
fi

# ── 3. -crisp：CRISPR 阵列检测（8 个直向重复 → 1 个 array）──────────────────
run crisp -crisp "$DATA/crisp_hits.gff" -out "$OUT/crisp_out.gff"
r=$(rc_of crisp)
n=$(wc -l < "$OUT/crisp_out.gff" 2>/dev/null | tr -d ' ')
piles=$(grep -c "Pile " "$OUT/crisp_out.gff" 2>/dev/null || true)
fam0=$(grep -c "Family 0 " "$OUT/crisp_out.gff" 2>/dev/null || true)
arrays=$(grep -c "^1 arrays" "$OUT/crisp.log" 2>/dev/null || true)
if [ "$r" = 0 ] && [ "$n" = 8 ] && [ "$piles" = 8 ] && [ "$fam0" = 8 ] && [ "${arrays:-0}" -ge 1 ]; then
    _record crisp PASS "rc=0, 1 array, 8 piles (Pile 0..7, Family 0)"
else
    _record crisp FAIL "rc=$r, records=$n piles=$piles family0=$fam0 expected 8/8/8"
fi

# ── 4. -trs：散在重复（4 拷贝元件 → 1 超家族 0.0）────────────────────────────
run trs -trs "$DATA/disp_hits.gff" -out "$OUT/trs.gff" \
        -piles "$OUT/trs_piles.gff" -images "$OUT/trs_images.gff"
r=$(rc_of trs)
ntrs=$(wc -l < "$OUT/trs.gff" 2>/dev/null | tr -d ' ')
npile=$(wc -l < "$OUT/trs_piles.gff" 2>/dev/null | tr -d ' ')
nimg=$(wc -l < "$OUT/trs_images.gff" 2>/dev/null | tr -d ' ')
fam=$(grep -c "Family 0.0" "$OUT/trs.gff" 2>/dev/null || true)
sf=$(grep -c "^1 superfamilies" "$OUT/trs.log" 2>/dev/null || true)
if [ "$r" = 0 ] && [ "$ntrs" = 4 ] && [ "$npile" = 4 ] && [ "$nimg" = 12 ] \
   && [ "$fam" = 4 ] && [ "${sf:-0}" -ge 1 ]; then
    _record trs PASS "rc=0, 1 superfamily / 4 TRS records / 4 piles / 12 images"
else
    _record trs FAIL "rc=$r, trs=$ntrs piles=$npile images=$nimg family0.0=$fam expected 4/4/12/4"
fi

# ── 5. -trs2fasta：家族 FASTA（依赖用例 4 的 trs.gff，对应上游 3a 步）───────
mkdir -p "$OUT/fams"
run trs2fasta -trs2fasta "$OUT/trs.gff" -seq "$DATA/disp_genome.fasta" \
              -path "$OUT/fams" -prefix syn
r=$(rc_of trs2fasta)
famfile="$OUT/fams/0.0"
nseq=$(grep -c "^>" "$famfile" 2>/dev/null || true)
pfx=$(grep -c "^>syn\.0\.0 " "$famfile" 2>/dev/null || true)
bp=$(awk '/^>/{next}{n+=length($0)}END{print n+0}' "$famfile" 2>/dev/null || echo 0)
if [ "$r" = 0 ] && [ "${nseq:-0}" = 4 ] && [ "${pfx:-0}" = 4 ] && [ "${bp:-0}" = 3600 ]; then
    _record trs2fasta PASS "rc=0, fams/0.0: 4 seqs labelled syn.0.0 / 3600 bp"
else
    _record trs2fasta FAIL "rc=$r, seqs=$nseq labelled=$pfx bp=$bp expected 4/4/3600"
fi

# ── 6. -tr：LTR 家族（4 个 ≥50kb 相隔的候选 → 1 家族）───────────────────────
run tr -tr "$DATA/ltr_hits.gff" -out "$OUT/ltr.gff" -cand "$OUT/ltr_cands.gff"
r=$(rc_of tr)
ntr=$(wc -l < "$OUT/ltr.gff" 2>/dev/null | tr -d ' ')
ncand=$(wc -l < "$OUT/ltr_cands.gff" 2>/dev/null | tr -d ' ')
nfam=$(grep -c "Family 0 ;" "$OUT/ltr.gff" 2>/dev/null || true)
if [ "$r" = 0 ] && [ "$ntr" = 4 ] && [ "$ncand" = 4 ] && [ "$nfam" = 4 ]; then
    _record tr PASS "rc=0, 4 LTR candidates → 1 family with 4 members"
else
    _record tr FAIL "rc=$r, families=$ntr cands=$ncand family0=$nfam expected 4/4/4"
fi

# ── 7. -tan：串联重复金字塔（1 pile 内 9 条嵌套命中）────────────────────────
run tan -tan "$DATA/tan_hits.gff" -out "$OUT/tan.gff" \
        -pyramid "$OUT/tan_pyr.gff" -motif "$OUT/tan_motif.txt"
r=$(rc_of tan)
ntan=$(wc -l < "$OUT/tan.gff" 2>/dev/null | tr -d ' ')
npyr=$(wc -l < "$OUT/tan_pyr.gff" 2>/dev/null | tr -d ' ')
nmot=$(wc -l < "$OUT/tan_motif.txt" 2>/dev/null | tr -d ' ')
pyr=$(grep -c "Pyramid 0" "$OUT/tan.gff" 2>/dev/null || true)
if [ "$r" = 0 ] && [ "$ntan" = 9 ] && [ "$npyr" = 1 ] && [ "${nmot:-0}" -ge 1 ] && [ "$pyr" = 9 ]; then
    _record tan PASS "rc=0, 1 pyramid / 9 hits / motif file emitted (${nmot} records)"
else
    _record tan FAIL "rc=$r, hits=$ntan pyramids=$npyr motif=$nmot expected 9/1/>=1"
fi

# ── 8. -tanmotif2fasta：motif → 家族 FASTA（依赖用例 7）────────────────────
mkdir -p "$OUT/tanfams"
run tanmotif2fasta -tanmotif2fasta "$OUT/tan_motif.txt" -seq "$DATA/tan_genome.fasta" \
                   -path "$OUT/tanfams" -prefix syn
r=$(rc_of tanmotif2fasta)
tf="$OUT/tanfams/0"
tnseq=$(grep -c "^>" "$tf" 2>/dev/null || true)
tpfx=$(grep -c "^>syn\.0 " "$tf" 2>/dev/null || true)
if [ "$r" = 0 ] && [ "${tnseq:-0}" -ge 1 ] && [ "${tpfx:-0}" = "${tnseq:-1}" ]; then
    _record tanmotif2fasta PASS "rc=0, tanfams/0 emitted with ${tnseq} sequences labelled syn.0"
else
    _record tanmotif2fasta FAIL "rc=$r, seqs=${tnseq:-0} labelled=${tpfx:-0} expected >=1"
fi

# ── 9. -cons：多序列比对一致性序列 ──────────────────────────────────────────
run cons -cons "$DATA/aln.fasta" -out "$OUT/cons.fasta" -label consensus_test
r=$(rc_of cons)
csq=$(sed -n '2p' "$OUT/cons.fasta" 2>/dev/null | tr -d '\r')
hdr=$(head -1 "$OUT/cons.fasta" 2>/dev/null | tr -d '\r')
if [ "$r" = 0 ] && [ "$hdr" = ">consensus_test" ] && [ "$csq" = "ACGTACGTACGGTACGTACGTACGT" ]; then
    _record cons PASS "rc=0, consensus == ACGTACGTACGGTACGTACGTACGT"
else
    _record cons FAIL "rc=$r, header='$hdr' seq='$csq' expected >consensus_test / 25 bp"
fi

# ── 10. -annot：第三方注释图示（RepeatMasker 风格）──────────────────────────
run annot -annot "$DATA/trs_in.gff" -rep "$DATA/reps.gff" -out "$OUT/annot.gff"
r=$(rc_of annot)
na=$(wc -l < "$OUT/annot.gff" 2>/dev/null | tr -d ' ')
abad=$(pics_badlen "$OUT/annot.gff")
named=$(grep -c "HETRP_DM(" "$OUT/annot.gff" 2>/dev/null || true)
if [ "$r" = 0 ] && [ "$na" = 4 ] && [ "$abad" = 0 ] && [ "${named:-0}" -ge 1 ]; then
    _record annot PASS "rc=0, 4 records / 20-char pictures / HETRP_DM annotated"
else
    _record annot FAIL "rc=$r, records=$na bad-pictures=$abad named=$named expected 4/0/>=1"
fi

# ── 11. -annotedge：边缘注释图示 ────────────────────────────────────────────
run annotedge -annotedge "$DATA/trs_in.gff" -rep "$DATA/reps.gff" -out "$OUT/annotedge.gff"
r=$(rc_of annotedge)
ne=$(wc -l < "$OUT/annotedge.gff" 2>/dev/null | tr -d ' ')
ebad=$(pics_badlen "$OUT/annotedge.gff")
if [ "$r" = 0 ] && [ "$ne" = 4 ] && [ "$ebad" = 0 ]; then
    _record annotedge PASS "rc=0, 4 records / 20-char edge pictures"
else
    _record annotedge FAIL "rc=$r, records=$ne bad-pictures=$ebad expected 4/0"
fi

# ── 12. 负向：缺少输出选项必须报错退出 ──────────────────────────────────────
run neg_missing_out -crisp "$DATA/crisp_hits.gff"
r=$(rc_of neg_missing_out)
if [ "$r" != 0 ] && grep -q "No output file specified" "$OUT/neg_missing_out.log"; then
    _record neg_missing_out PASS "rc=$r (non-zero) + 'No output file specified'"
else
    _record neg_missing_out FAIL "rc=$r, expected non-zero + 'No output file specified'"
fi

# ── 13. 负向：畸形 GFF 必须报 FATAL ERROR（不得静默产出）────────────────────
run neg_bad_gff -crisp "$DATA/bad.gff" -out "$OUT/neg_bad_out.gff"
r=$(rc_of neg_bad_gff)
if [ "$r" != 0 ] && grep -q "FATAL ERROR" "$OUT/neg_bad_gff.log"; then
    _record neg_bad_gff PASS "rc=$r (non-zero) + 'FATAL ERROR' reported"
else
    _record neg_bad_gff FAIL "rc=$r, expected non-zero + 'FATAL ERROR'"
fi

# ── 14. -multihit：TRS 多命中覆盖模式（上游可选 flag）──────────────────────
run multihit -trs "$DATA/disp_hits.gff" -out "$OUT/multihit_trs.gff" -multihit
r=$(rc_of multihit)
mh=$(wc -l < "$OUT/multihit_trs.gff" 2>/dev/null | tr -d ' ')
mhfam=$(grep -c "Family 0.0" "$OUT/multihit_trs.gff" 2>/dev/null || true)
mhsf=$(grep -c "^1 superfamilies" "$OUT/multihit.log" 2>/dev/null || true)
if [ "$r" = 0 ] && [ "$mh" = 4 ] && [ "$mhfam" = 4 ] && [ "${mhsf:-0}" -ge 1 ]; then
    _record multihit PASS "rc=0, 1 superfamily / 4 TRS records under -multihit"
else
    _record multihit FAIL "rc=$r, records=$mh family0.0=$mhfam superfamilies=${mhsf:-0} expected 4/4/>=1"
fi

# ── 15. -quiet：抑制全部进度输出且不改变结果文件（与用例 3 输出逐字节比对）──
run quiet -crisp "$DATA/crisp_hits.gff" -out "$OUT/quiet_crisp.gff" -quiet
r=$(rc_of quiet)
qbytes=$(wc -c < "$OUT/quiet.log" 2>/dev/null | tr -d ' ')
same=1
if command -v cmp >/dev/null 2>&1; then
    cmp -s "$OUT/crisp_out.gff" "$OUT/quiet_crisp.gff" && same=0
elif command -v md5sum >/dev/null 2>&1; then
    [ "$(md5sum < "$OUT/crisp_out.gff")" = "$(md5sum < "$OUT/quiet_crisp.gff")" ] && same=0
fi
if [ "$r" = 0 ] && [ "$same" = 0 ] && [ "${qbytes:-1}" = 0 ]; then
    _record quiet PASS "rc=0, output byte-identical to case 3, progress fully suppressed (0 bytes)"
else
    _record quiet FAIL "rc=$r, identical=$same stderr_bytes=${qbytes:-?} expected rc=0/identical/0"
fi

# ── 16. -exact：-cons 仅保留全保守列的最长连续块 ────────────────────────────
run exact -cons "$DATA/aln.fasta" -out "$OUT/cons_exact.fasta" -label consensus_exact -exact
r=$(rc_of exact)
ehdr=$(head -1 "$OUT/cons_exact.fasta" 2>/dev/null | tr -d '\r')
eseq=$(sed -n '2p' "$OUT/cons_exact.fasta" 2>/dev/null | tr -d '\r')
if [ "$r" = 0 ] && [ "$ehdr" = ">consensus_exact" ] && [ "$eseq" = "ACGT" ]; then
    _record exact PASS "rc=0, longest fully-conserved block == ACGT"
else
    _record exact FAIL "rc=$r, header='$ehdr' seq='$eseq' expected >consensus_exact / ACGT"
fi

TOTAL=$((PASS + FAIL + SKIP))
echo "──────────────────────────────────────────────────────────────"
echo "TOTAL=$TOTAL PASS=$PASS FAIL=$FAIL SKIP=$SKIP"
echo "SUMMARY_FILE=$SUMMARY"
[ "$FAIL" = 0 ] || exit 1
exit 0
