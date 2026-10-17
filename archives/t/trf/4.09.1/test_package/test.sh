#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer functional test for the trf executable.
# Runs inside the conanrun env (PATH includes the installed bin/).
# Mirrors the upstream manual sample (test_seqs.fasta -> test_seqs.txt):
# a default-parameter run (-d data table) must produce the repeat report
# with the expected patterns.  /tmp is read-only on OHOS — use $HOME/tmp.
#
# Known upstream behavior: TRF 4.09 returns the number of processed
# sequences as its exit code (1 for one sequence, 2 for two — observed on
# clean, complete runs); assertions therefore target the produced reports,
# and the exit code only guards against crashes (>=128).
set -euo pipefail

SCRATCH="${TMPDIR:-$HOME/tmp}/trf-test-$$"
mkdir -p "$SCRATCH"
trap 'rm -rf "$SCRATCH"' EXIT

cat > "$SCRATCH/sample.fasta" <<'EOF'
>0
TCATCGGTCATCGGTCATCGGTCATCGGTCATCGG
>1
ACCCCTCAGGGTACCCCTCAGGGTACCCCTCAGGGTACCCCTCAGGGTACCCCTCAGGGTACCCCTCAGGGTACCCCTCAGGGT
EOF

echo "[test] trf default-parameter run on sample fasta"
cd "$SCRATCH"
set +e
trf sample.fasta 2 7 7 80 10 50 500 -d > trf-stdout.log 2> trf-stderr.log
RC=$?
set -e
[ "$RC" -lt 128 ] || {
    echo "FAIL: trf crashed (exit $RC, signal?)"
    cat trf-stdout.log trf-stderr.log
    exit 1
}
echo "OK: trf completed (exit $RC, upstream returns the processed sequence count)"

DAT="sample.fasta.2.7.7.80.10.50.500.dat"
[ -s "$DAT" ] || {
    echo "FAIL: data table $DAT not produced"
    ls -la
    cat trf-stdout.log trf-stderr.log
    exit 1
}
echo "OK: data table produced ($DAT)"

for pattern in TCATCGG ACCCCTCAGGGT; do
    grep -q "$pattern" "$DAT" || {
        echo "FAIL: expected repeat pattern $pattern not found in $DAT"
        cat "$DAT"
        exit 1
    }
    echo "OK: repeat pattern $pattern reported"
done

# Multi-sequence runs name the per-sequence text reports s1/s2/...
grep -q "Period size: 7" sample.fasta.s1.*.txt.html || {
    echo "FAIL: expected 'Period size: 7' header in s1 text report"
    cat sample.fasta.*.txt.html
    exit 1
}
echo "OK: text report carries the repeat table header"
echo "ALL CONSUMER TESTS PASSED"
