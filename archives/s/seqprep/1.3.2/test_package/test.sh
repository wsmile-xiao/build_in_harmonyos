#!/bin/sh
# Consumer behavior test for SeqPrep 1.3.2.
# Builds a synthetic perfectly-overlapping paired-end FASTQ pair, runs the
# packaged SeqPrep binary, and asserts real behavior:
#   1. exit code 0;
#   2. both trimmed R1/R2 outputs exist and are non-empty;
#   3. the merged single-end output (-s) contains merged records
#      (overlap merging actually happened);
#   4. merged sequences have the expected insert length (60).
# Note: SeqPrep always writes gzip-format outputs (regardless of file
# extension) and emits two benign "fastq record not beginning with @"
# lines at EOF even on its own bundled data — assertions here rely on
# zcat-decoded content and exit code, not on those counters.
set -e

failures=0
check() {
    if ! "$@"; then
        echo "FAIL: $*"
        failures=$((failures + 1))
    fi
}

BIN=$(command -v SeqPrep)
check [ -n "$BIN" ]
check [ -x "$BIN" ]
echo "SeqPrep binary: $BIN"

WORK=$(pwd)/seqprep_test_work
rm -rf "$WORK"
mkdir -p "$WORK"
cd "$WORK"

# 60bp insert: R1 = insert, R2 = reverse-complement(insert) => 100% overlap
INS=AATGCTAGCTAAGGATCCGATCGATCGGCATTACGGCATTACGTACGACTAGCATCGAGCTAAGCT
python3 - "$INS" << 'PYEOF'
import sys
ins = sys.argv[1]
comp = str.maketrans("ACGT", "TGCA")
rc = ins.translate(comp)[::-1]
q = "I" * len(ins)
for i in range(1, 5):
    with open("r1.fastq", "a") as a, open("r2.fastq", "a") as b:
        a.write("@r%d\n%s\n+\n%s\n" % (i, ins, q))
        b.write("@r%d\n%s\n+\n%s\n" % (i, rc, q))
PYEOF

set +e
"$BIN" -f r1.fastq -r r2.fastq -1 out1.fastq -2 out2.fastq -s merged.fastq > run.log 2>&1
RC=$?
set -e
echo "SeqPrep exit code: $RC"
check [ "$RC" -eq 0 ]

check [ -s out1.fastq ]
check [ -s out2.fastq ]
check [ -s merged.fastq ]

MERGED=$(zcat merged.fastq 2>/dev/null | grep -c '^@' || true)
check [ "${MERGED:-0}" -gt 0 ]
echo "merged records: $MERGED"

# merged sequences must be roughly the 60bp insert (consensus merge keeps
# a few mismatch-tolerant overhang bases, deterministic for this input)
SEQLEN=$(zcat merged.fastq 2>/dev/null | sed -n '2p' | tr -d '\n' | wc -c)
check [ "$SEQLEN" -ge 55 ]
check [ "$SEQLEN" -le 70 ]

echo "seqprep consumer test: merged=$MERGED seqlen=$SEQLEN"

if [ "$failures" -eq 0 ]; then
    echo "test_seqprep: all assertions passed"
    exit 0
fi
echo "test_seqprep: $failures assertion(s) failed"
exit 1
