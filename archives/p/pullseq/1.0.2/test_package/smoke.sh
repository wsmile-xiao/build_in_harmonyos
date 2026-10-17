#!/bin/sh
# Consumer smoke test for pullseq 1.0.2: exercise the packaged pullseq on a
# small FASTA fixture (extract by name list and by regex).
# Usage: smoke.sh <package_bindir>
# POSIX sh only; scratch work under mktemp.
BINDIR="$1"

if [ -z "$BINDIR" ] || [ ! -x "$BINDIR/pullseq" ]; then
    echo "smoke: missing packaged pullseq under $BINDIR" >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$HOME/tmp"
WORK="$(mktemp -d "$HOME/tmp/pullseq-smoke.XXXXXX")" || exit 1
trap 'rm -rf "$WORK"' EXIT

# Runaway-memory guard: this binary is tiny, so a multi-GB footprint means a
# defect (or an accidental huge input); cap address space so it dies with
# ENOMEM instead of taking the shared device / CI worker down.  POSIX sh does
# not mandate -v, so ignore failure where unsupported.
ulimit -v 2097152 2>/dev/null || true

# Build a two-record FASTA fixture.
printf ">seq1\nACGTACGTAC\n>seq2\nTTAATTAAGG\n" > "$WORK/in.fa"

# 1) Extraction by name list.
echo "seq2" > "$WORK/names.txt"
"$BINDIR/pullseq" -i "$WORK/in.fa" -n "$WORK/names.txt" > "$WORK/byname.fa" 2>"$WORK/e1"
RC=$?
if [ $RC -ne 0 ]; then
    echo "smoke: pullseq -n failed rc=$RC ($(head -2 "$WORK/e1"))" >&2
    exit 1
fi
grep -q "seq2" "$WORK/byname.fa" || { echo "smoke: -n output missing seq2" >&2; exit 1; }
grep -q "TTAATTAAGG" "$WORK/byname.fa" || { echo "smoke: -n output missing seq2 bases" >&2; exit 1; }
grep -q "seq1" "$WORK/byname.fa" && { echo "smoke: -n output leaked seq1" >&2; exit 1; }

# 2) Extraction by case-insensitive regex.
"$BINDIR/pullseq" -i "$WORK/in.fa" -g "SEQ1" > "$WORK/byre.fa" 2>"$WORK/e2"
RC=$?
if [ $RC -ne 0 ]; then
    echo "smoke: pullseq -g failed rc=$RC ($(head -2 "$WORK/e2"))" >&2
    exit 1
fi
grep -q "ACGTACGTAC" "$WORK/byre.fa" || { echo "smoke: -g output missing seq1 bases" >&2; exit 1; }
grep -q "seq2" "$WORK/byre.fa" && { echo "smoke: -g output leaked seq2" >&2; exit 1; }

echo "pullseq consumer OK: name-list and regex extraction"
exit 0
