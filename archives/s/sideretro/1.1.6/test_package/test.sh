#!/usr/bin/env bash
# test_package/test.sh — sideretro CLI 完整消费者用例（R34 端到端）
# 在 conanrun 环境运行（PATH 含安装的 bin/，LD_LIBRARY_PATH 含依赖库）
#
# 覆盖：
#  1) sider --version / --cite / 无参数 usage（CLI 骨架断言）
#  2) 完整消费者用例：构造最小 SAM+GTF 输入，真实跑通
#     process-sample → merge-call → make-vcf 全流程，验证 VCF 产物生成
#     （端到端：非纯断言，真实调用被测包功能流程）
#
# 注意：OHOS /tmp 为只读 erofs，临时输出必须写可写目录（$HOME/tmp）。
set -euo pipefail

BIN_DIR="$1"
SIDER="$BIN_DIR/sider"

if [ ! -x "$SIDER" ]; then
    echo "FAIL: sider 不存在或不可执行: $SIDER"
    exit 1
fi

# 可写临时目录：优先 TMPDIR，否则 $HOME/tmp（OHOS /tmp 只读）
if [ -z "${TMPDIR:-}" ] || ! touch "$TMPDIR/.wtest" 2>/dev/null; then
    TMPDIR="${HOME}/tmp"
    mkdir -p "$TMPDIR"
fi
WORK=$(mktemp -d "${TMPDIR}/sider-e2e.XXXXXX")
trap 'rm -rf "$WORK"' EXIT
OUT="$WORK/out.txt"

# ── 1. CLI 骨架断言 ─────────────────────────────────────────────
echo "[test] sider --version -> PACKAGE_STRING"
"$SIDER" --version >"$OUT" 2>&1
grep -q "sideRETRO" "$OUT"
echo "OK: --version 输出含 sideRETRO"

echo "[test] sider --cite -> BibTeX"
"$SIDER" --cite >"$OUT" 2>&1
grep -q "@article" "$OUT"
echo "OK: --cite 输出含 @article"

echo "[test] sider (no args) -> usage"
"$SIDER" >"$OUT" 2>&1
grep -q "Usage:" "$OUT"
echo "OK: 无参数输出含 Usage:"

# ── 2. 完整消费者用例：端到端功能流程 ────────────────────────────
# 构造最小输入：1 条 mapped read + 2 条 unmapped read 的 SAM，
# 以及带 exon 记录的 GTF 注释（process-sample 要求 exon + protein_coding）
echo "[e2e] 构造最小 SAM + GTF 输入"
SAM="$WORK/test.sam"
GTF="$WORK/test.gtf"
cat > "$SAM" << 'SAME'
@SQ	SN:PONGA	LN:520052
ponga1	0	PONGA	35361	0	10M	*	0	0	ATCGATCGAT	!!!!!!!!!!	NM:i:0	AS:i:52	XS:i:52
ponga2	4	*	0	0	*	*	0	0	ATCGATCGAA	!!!!!!!!!!	AS:i:0	XS:i:0
ponga3	4	*	0	0	*	*	0	0	ATCGATCGAA	!!!!!!!!!!	AS:i:0	XS:i:0
SAME
cat > "$GTF" << 'GTFE'
chr1	.	gene	1000	1100	100	+	.	gene_name=g1;gene_id=ENSG1;transcript_id=ENST1;transcript_type=protein_coding;
chr1	.	transcript	1000	1100	.	+	.	gene_name=g1;gene_id=ENSG1;transcript_id=ENST1;transcript_type=protein_coding;
chr1	.	exon	1000	1100	.	+	1	gene_name=g1;gene_id=ENSG1;transcript_id=ENST1;transcript_type=protein_coding;exon_id=ENSE1;
GTFE

echo "[e2e] process-sample -> 生成 SQLite 数据库"
"$SIDER" process-sample -q -a "$GTF" -o "$WORK/ps" -p e2e "$SAM" >"$OUT" 2>&1
test -f "$WORK/ps/e2e.db"
echo "OK: process-sample 生成 e2e.db"

echo "[e2e] merge-call --in-place -> 注释数据库"
"$SIDER" merge-call --in-place "$WORK/ps/e2e.db" >"$OUT" 2>&1
test -f "$WORK/ps/e2e.db"
echo "OK: merge-call 完成（db 存在）"

echo "[e2e] make-vcf -> 生成 VCF 产物"
"$SIDER" make-vcf -o "$WORK/vcf" -p e2e "$WORK/ps/e2e.db" >"$OUT" 2>&1
test -f "$WORK/vcf/e2e.vcf"
grep -q "##fileformat=VCF" "$WORK/vcf/e2e.vcf"
echo "OK: make-vcf 生成 e2e.vcf（含 VCF header）"

echo "ALL TESTS PASSED"
