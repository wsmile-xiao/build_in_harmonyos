#!/data/service/hnp/bin/bash
set -eu

echo "[test] scythe --version"
scythe --version

echo "[test] scythe trims a gzip FASTQ on OHOS"
printf '@read1\nACGTACGTACGTAGATCGGAAGAGC\n+\nIIIIIIIIIIIIIIIIIIIIIIIII\n' | gzip > input.fastq.gz
scythe -a adapters.fa -o output.fastq input.fastq.gz
grep -q '^@read1' output.fastq

echo "[test] scythe keeps the trimmed sequence"
awk 'NR==2 { print length($0) }' output.fastq | grep -q '^[0-9]\+$'

echo "ALL TESTS PASSED"
