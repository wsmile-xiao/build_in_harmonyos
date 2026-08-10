#!/bin/sh
set -eu

AdapterRemoval --version 2> version.txt
grep -q "AdapterRemoval ver. 2.3.4" version.txt

cat > reads.fq <<'EOF'
@read1
ACGTACGTACGTACGTACGT
+
IIIIIIIIIIIIIIIIIIII
EOF

AdapterRemoval \
  --file1 reads.fq \
  --output1 trimmed.fq \
  --settings settings.txt \
  --discarded discarded.fq \
  --threads 1 \
  2> run.log

test -s trimmed.fq
grep -q "^@read1" trimmed.fq
grep -q "ACGTACGTACGTACGTACGT" trimmed.fq
