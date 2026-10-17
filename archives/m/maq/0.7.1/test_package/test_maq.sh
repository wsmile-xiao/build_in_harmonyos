#!/usr/bin/env bash
# maq 0.7.1 — test_package 驱动脚本（消费者视角）
# 驱动安装后的 `maq`（PATH 由 conanrun 提供）跑通上游 maq.pod EXAMPLES 的关键流程。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SAMPLES="$SCRIPT_DIR/sampledata"
WORK="$PWD/maq-testwork"
rm -rf "$WORK"; mkdir -p "$WORK"
trap 'cd "$SCRIPT_DIR" 2>/dev/null || true; rm -rf "$WORK"' EXIT
cd "$WORK"
cp "$SAMPLES/ref.fasta" "$SAMPLES/part1.fastq" "$SAMPLES/part2.fastq" .

echo "== 1. maq 版本 =="
# `maq` 无参数打印用法到 stderr 并以 rc=1 退出（上游行为）
MAQ_USAGE="$(maq 2>&1 || true)"
echo "$MAQ_USAGE" | grep -q 'Version: 0.7.1'

echo "== 2. fasta2bfa =="
maq fasta2bfa ref.fasta ref.bfa
test -s ref.bfa

echo "== 3. fastq2bfq (paired) =="
maq fastq2bfq part1.fastq part1.bfq
maq fastq2bfq part2.fastq part2.bfq
test -s part1.bfq && test -s part2.bfq

echo "== 4. map (paired-end) =="
maq map -a 300 aln.map ref.bfa part1.bfq part2.bfq 2> map.log
test -s aln.map
grep -q 'mapped' map.log

echo "== 5. assemble =="
maq assemble cns.cns ref.bfa aln.map 2> assemble.log
test -s cns.cns
# cns.cns 为 gzip 压缩的自有格式，用 cns2ref 解出参考序列做内容断言
maq cns2ref cns.cns > cns.ref
grep -q '^>chr1' cns.ref

echo "== 6. mapstat / mapview =="
maq mapstat aln.map > mapstat.txt
test -s mapstat.txt
maq mapview aln.map > mapview.txt
test -s mapview.txt

echo "maq test_package: PASS"
