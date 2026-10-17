#!/bin/sh
# jellyfish1 CLI behaviour assertions.
#
# Input is two identical 8 bp reads.  For -m 4 the interior 4-mers are fully
# enumerable by hand: each read contributes AACG ACCG CCGG CGGT GGTT, so
# CCGG and ACCG must come back with count 2 and ACGT (absent, and its own
# reverse complement) with count 0.  Only values derived that way are asserted:
# jellyfish 1.1 pads the tail of the parsed block with T bases, so aggregate
# numbers such as the total entry count are not independently derivable for a
# tiny fixture and are deliberately not claimed here.
#
# query takes the database as its only argument and reads the k-mers from
# stdin, printing "KMER COUNT" per line; count -o PREFIX writes PREFIX_0.
set -e
rm -f db_0 db.stats dump.txt q.txt d2.txt 2>/dev/null || true

./jf.sh count -m 4 -s 10M -t 1 -o db --stats db.stats test.fa
if [ ! -s db_0 ]; then echo "FAIL db_0 missing or empty"; exit 1; fi
if [ ! -s db.stats ]; then echo "FAIL stats file missing or empty"; exit 1; fi

./jf.sh dump -c db_0 > dump.txt
if [ ! -s dump.txt ]; then echo "FAIL dump empty"; exit 1; fi
N=$(grep -c "^CCGG 2$" dump.txt)
if [ "$N" != "1" ]; then echo "FAIL dump line CCGG 2 count=$N"; exit 1; fi

printf "CCGG\n" | ./jf.sh query db_0 > q.txt
read K V < q.txt
if [ "$K" != "CCGG" ] || [ "$V" != "2" ]; then echo "FAIL query CCGG got $K $V"; exit 1; fi

printf "ACCG\n" | ./jf.sh query db_0 > q.txt
read K V < q.txt
if [ "$K" != "ACCG" ] || [ "$V" != "2" ]; then echo "FAIL query ACCG got $K $V"; exit 1; fi

printf "ACGT\n" | ./jf.sh query db_0 > q.txt
read K V < q.txt
if [ "$K" != "ACGT" ] || [ "$V" != "0" ]; then echo "FAIL query ACGT got $K $V"; exit 1; fi

rm -f db_0 2>/dev/null || true
./jf.sh count -m 4 -s 10M -t 4 -o db test.fa
printf "CCGG\n" | ./jf.sh query db_0 > q.txt
read K V < q.txt
if [ "$K" != "CCGG" ] || [ "$V" != "2" ]; then echo "FAIL 4-thread query CCGG got $K $V"; exit 1; fi

./mmap_probe db_0
echo "ALL_CLI_ASSERTIONS_PASSED"
