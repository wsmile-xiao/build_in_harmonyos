#!/data/service/hnp/bin/bash
# test_package/test.sh — functional smoke test for bedtools
# Runs in the conanrun environment (PATH includes the installed bin/).
# Exercises real bedtools subcommands with assertions (R34), not just --version.
set -euo pipefail

echo "[test] bedtools --version"
bedtools --version

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# Two interval sets. a = [10,20) [30,40);  b = [15,25) [35,45).
printf "chr1\t10\t20\nchr1\t30\t40\n" > "$WORK/a.bed"
printf "chr1\t15\t25\nchr1\t35\t45\n" > "$WORK/b.bed"

# bedtools intersect -> expected overlap [15,20) and [35,40).
printf "chr1\t15\t20\nchr1\t35\t40\n" > "$WORK/expected.txt"
bedtools intersect -a "$WORK/a.bed" -b "$WORK/b.bed" > "$WORK/got.txt"
if cmp -s "$WORK/expected.txt" "$WORK/got.txt"; then
    echo "[test] bedtools intersect: PASS"
else
    echo "[test] bedtools intersect: FAIL"
    echo "--- expected ---"; cat "$WORK/expected.txt"
    echo "--- got ---"; cat "$WORK/got.txt"
    exit 1
fi

# bedtools sort should leave an already-sorted file unchanged.
bedtools sort -i "$WORK/b.bed" > "$WORK/sorted.txt"
if cmp -s "$WORK/b.bed" "$WORK/sorted.txt"; then
    echo "[test] bedtools sort: PASS"
else
    echo "[test] bedtools sort: FAIL"
    exit 1
fi

echo "✅ bedtools functional tests OK"
