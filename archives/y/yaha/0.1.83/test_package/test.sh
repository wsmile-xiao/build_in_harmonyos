#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
data_dir="$script_dir/data"
tmp_root="${TMPDIR:-${HOME:?}/tmp}"
mkdir -p "$tmp_root"
work_dir="$(mktemp -d "$tmp_root/yaha test.XXXXXX")"
trap 'rm -rf "$work_dir"' EXIT

cp "$data_dir/reference.fa" "$work_dir/reference.fa"
cp "$data_dir/reads.fa" "$work_dir/reads.fa"
cp "$data_dir/reads.fq" "$work_dir/reads.fq"
cd "$work_dir"

yaha -xh >/dev/null
yaha -g reference.fa
yaha -x reference.X15_01_65525S -q reads.fa -osh fasta.sam -t 2
yaha -x reference.X15_01_65525S -q reads.fq -osh fastq.sam -t 2

check_sam_record() {
    local sam_file="$1"
    local expected_qname="$2"
    awk -F '\t' -v qname="$expected_qname" '
        $1 == qname && $2 == "0" && $3 == "chr1" && $4 == "21" && $6 == "50M" { found = 1 }
        END {
            if (!found) {
                printf "Expected mapped SAM record for %s was not found in %s\n", qname, FILENAME > "/dev/stderr"
                exit 1
            }
        }
    ' "$sam_file"
}

check_sam_record fasta.sam fasta1
check_sam_record fastq.sam fastq1
printf '%s\n' 'PASS: FASTA and FASTQ reads mapped to chr1:21 with 50M using two threads.'
