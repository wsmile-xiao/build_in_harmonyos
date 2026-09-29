#!/bin/sh
# ============================================================================
# OHOS consumer case for lucy 1.20  —  test_package layer (消费者视角验证)
#
# This is the HarmonyOS-specific case added on top of the upstream suite
# (docs/TEST_QUALITY_SPEC §4, PR 模板「鸿蒙特有测试」行).  It does not repeat the
# upstream golden comparison; it demonstrates that a downstream consumer can
# actually use the *installed* lucy binary on OHOS, end to end:
#
#   1. a real Sanger-style read set (6 reads, 608-651 bp, phred qualities)
#      extracted from upstream's own `atie` fixture -> data/reads.{seq,qul}
#   2. the installed `lucy` performs quality + vector trimming using the
#      upstream vector/splice fixtures -> data/PUC19, data/PUC19splice
#   3. lucy's coordinate report is consumed by upstream's own zapping.awk
#      (README.FIRST FAQ #1) to materialise the trimmed FASTA
#
# The 2nd/ABI sequence is intentionally omitted: that step is the one that
# consumes libc random() (see check/golden-compare.py), so leaving it out keeps
# this case byte-deterministic while still exercising quality trim, splice
# detection, vector identification and the downstream extraction path.
#
# This case is deliberately *not* an assertion suite — every step is a real
# execution, the exit status of each step is the result, and the artefacts it
# produced are inventoried at the end.  `set -e` turns any failed step into a
# failed case (which is also what makes the CI destructive negative test L1e
# meaningful: with the package's bin/ removed, `lucy` cannot be resolved).
#
# Usage: consumer_case.sh [workdir]
#   When no workdir is given a scratch directory is created outside the recipe
#   tree (so runtime artefacts can never be picked up by a commit) and removed
#   again on exit.  Pass an explicit path to keep the artefacts for inspection.
# ============================================================================
set -eu

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
DATA="$HERE/data"

if [ ! -d "$DATA" ]; then
    echo "FATAL: consumer fixture directory '$DATA' is missing"
    exit 2
fi

WORK=${1:-}
if [ -z "$WORK" ]; then
    for base in "${TMPDIR:-}" /tmp "${HOME:-}/.cache"; do
        [ -n "$base" ] && [ -d "$base" ] && [ -w "$base" ] || continue
        WORK="$base/lucy-ohos-consumer-case.$$"
        break
    done
fi
# Last resort: OHOS images can expose no writable TMPDIR/tmp/cache at all.
[ -n "$WORK" ] || WORK="$HERE/consumer-work.$$"

cleanup() { rm -rf "$WORK" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

rm -rf "$WORK"
mkdir -p "$WORK"
cd "$WORK"

cp "$DATA/reads.seq" "$DATA/reads.qul" \
   "$DATA/PUC19" "$DATA/PUC19splice" "$DATA/zapping.awk" .

echo "consumer case workdir : $(pwd)"
echo "lucy consumed from    : $(command -v lucy)"
echo "read set              : $(grep -c '^>' reads.seq) reads, $(wc -c < reads.seq) bytes of sequence + $(wc -c < reads.qul) bytes of quality"
"lucy" 2>&1 | sed -n '1,2p' || true

echo ""
echo "--- step 1/3: lucy quality + vector trimming -----------------------------"
# NOTE: always pass an explicit -debug file name.  lucy's default debug name is
# "lucy.debug", i.e. upstream's golden reference file; a bare `-debug` would
# overwrite it (README.FIRST §Testing chooses `lucy.info` for exactly this
# reason).
lucy -v PUC19 PUC19splice reads.seq reads.qul \
     -output trimmed.seq trimmed.qul -debug trimmed.info
echo "lucy exit status: 0"

echo ""
echo "--- step 2/3: consumer post-processing (upstream zapping.awk) ------------"
awk -f zapping.awk trimmed.seq > clean.seq
echo "trimmed sequences physically extracted into clean.seq"

echo ""
echo "--- step 3/3: per-read consumer view ------------------------------------"
# trimmed.info columns: name CLR l r CLB l r CLN l r CLZ l r CLV l r
awk -F'\t' '{len = ($4 > 0 && $4 >= $3) ? ($4 - $3 + 1) : 0;
    printf "  %-12s clean-range %s-%s (%s bp)  vector-trim %s-%s  vector-match-zone %s-%s\n", \
    $1, $3, $4, len, $15, $16, $12, $13}' trimmed.info

echo ""
echo "--- produced artefacts --------------------------------------------------"
for f in trimmed.info trimmed.seq trimmed.qul clean.seq; do
    printf "  %-14s %6s lines  %8s bytes\n" "$f" "$(wc -l < "$f")" "$(wc -c < "$f")"
done
echo "  clean.seq records: $(grep -c '^>' clean.seq) / input reads: $(grep -c '^>' reads.seq)"
echo "  scratch workdir   : $WORK (removed on exit)"
echo ""
echo "first 3 lines of the consumed result:"
sed -n '1,3p' clean.seq | sed 's/^/  /'

echo ""
echo "=========================================================================="
echo "OHOS-CASE ohos-consumer-quality-vector-trim: PASS (artefacts listed above)"
echo "=========================================================================="
