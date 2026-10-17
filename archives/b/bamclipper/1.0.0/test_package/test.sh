#!/usr/bin/env bash
set -euo pipefail

bamclipper=${1:?bamclipper path required}
samtools=${2:?samtools path required}
parallel=${3:?parallel path required}
perl=${4:?perl path required}
bash=${5:?bash path required}
perl_root=$(cd "$(dirname "$perl")/.." && pwd)
perl5lib=$(find "$perl_root/lib/perl5" -type d | LC_ALL=C sort | paste -sd: -)
export PERL5LIB="$perl5lib${PERL5LIB:+:$PERL5LIB}"

work_dir=$(mktemp -d "${TMPDIR:-/tmp}/bamclipper-test.XXXXXX")
trap 'rm -rf "$work_dir"' EXIT
cd "$work_dir"

test -x "$bamclipper"
test -x "$(dirname "$bamclipper")/clipprimer.pl"
test -x "$(dirname "$bamclipper")/injectseparator.pl"
test -x "$samtools"
test -x "$parallel"
test -x "$perl"
test -x "$bash"

"$bash" "$bamclipper" >/dev/null 2>&1 && exit 1 || test "$?" -eq 1

cat > primers.bedpe <<'EOF'
chr1	9	19	chr1	29	39	primer1
EOF
cat > reads.sam <<'EOF'
@HD	VN:1.6	SO:queryname
@SQ	SN:chr1	LN:1000
read1	99	chr1	10	60	20M	=	20	30	ACGTACGTACACGTACGTAC	FFFFFFFFFFFFFFFFFFFF
read1	147	chr1	20	60	20M	=	10	-30	TGCATGCATGTGCATGCATG	FFFFFFFFFFFFFFFFFFFF
EOF

"$samtools" view -bS reads.sam > input.bam
"$samtools" index input.bam
"$bash" "$bamclipper" -b input.bam -p primers.bedpe -n 1 -s "$samtools" -g "$parallel"
test -s input.primerclipped.bam
test -s input.primerclipped.bam.bai
"$samtools" quickcheck input.primerclipped.bam
count=$("$samtools" view -c input.primerclipped.bam)
test "$count" -eq 2
"$samtools" view input.primerclipped.bam > clipped.sam
awk -F '\t' '$1 == "read1" && $2 == 99 && $4 == 20 && $6 == "10S10M" {forward=1} $1 == "read1" && $2 == 147 && $4 == 20 && $6 == "10M10S" {reverse=1} END {exit !(forward && reverse)}' clipped.sam
printf 'PASS: bamclipper soft-clipped both primer ends to 10S10M and 10M10S\n'

printf '@HD\tVN:1.6\tSO:queryname\n@SQ\tSN:chr1\tLN:1000\nread1\t99\tchr1\t10\t60\t10M\t=\t30\t30\tACGTACGTAC\tFFFFFFFFFF\nread1\t147\tchr1\t30\t60\t10M\t=\t10\t-30\tTGCATGCATG\tFFFFFFFFFF\nread2\t99\tchr1\t50\t60\t10M\t=\t70\t30\tACGTACGTAC\tFFFFFFFFFF\nread2\t147\tchr1\t70\t60\t10M\t=\t50\t-30\tTGCATGCATG\tFFFFFFFFFF\n' |
  "$perl" "$(dirname "$bamclipper")/injectseparator.pl" | grep -q '^__'
printf 'PASS: injectseparator.pl separates consecutive read pairs\n'
