#!/bin/sh
#--------------------------------------------------------------------
# Consumer test for kgb 1.0b5 (installed kgb archiver).
#
# Env:
#   KGB_BIN      path to the installed kgb executable
#   KGB_LICENSE  path to the installed LICENSE file
# Exit: 0 = all checks passed, 1 = failure
#--------------------------------------------------------------------
set -eu

KGB="${KGB_BIN:?KGB_BIN must point to the installed kgb executable}"
LIC="${KGB_LICENSE:?KGB_LICENSE must point to the installed LICENSE file}"

WORK="${TMPDIR:-.}/kgb-test.$$"
mkdir -p "$WORK" || { echo "FAIL: cannot create workdir $WORK"; exit 1; }
cd "$WORK"
trap 'cd /; rm -rf "$WORK"' EXIT

checks=0
fails=0

check() { # check <name> <actual> <expected> [dumpfile]
	checks=$((checks + 1))
	if [ "$2" = "$3" ]; then
		echo "PASS: $1"
	else
		echo "FAIL: $1 (got '$2', want '$3')"
		if [ -n "${4:-}" ] && [ -f "$4" ]; then
			echo "--- $4 ---"; head -20 "$4"; echo "--- end ---"
		fi
		fails=$((fails + 1))
	fi
}

md5of() { md5sum "$1" | cut -d' ' -f1; }

# 1-2. no arguments -> usage banner on stdout, non-zero exit
"$KGB" > usage.txt 2>&1 && rc=0 || rc=$?
check "kgb without arguments exits non-zero" "$([ "$rc" -ne 0 ] && echo 0 || echo 1)" 0
check "kgb prints its usage banner" "$(grep -c -F 'KGB Archiver v1.0' usage.txt)" 1

# Build a deterministic input file
i=1
: > data.txt
while [ "$i" -le 200 ]; do
	echo "line $i: the quick brown fox jumps over the lazy dog" >> data.txt
	i=$((i + 1))
done
SUM_ORIG=$(md5of data.txt)

# 3-4. compress at -0, archive carries the KGB magic
"$KGB" -0 round.kgb data.txt > c.log 2>&1 && rc=0 || rc=$?
check "kgb -0 compress exits 0" "$rc" 0 c.log
check "archive carries the KGB_arch magic" "$(grep -c -F 'KGB_arch' round.kgb)" 1

# 5-6. extract byte-exact
rm -f data.txt
"$KGB" round.kgb > x.log 2>&1 && rc=0 || rc=$?
check "kgb extract exits 0" "$rc" 0 x.log
check "extracted file is byte-identical" "$(md5of data.txt)" "$SUM_ORIG"

# 7. default-level archive of the shipped LICENSE has the checksum asserted by
#    Debian's own test (deterministic archive format).
cp "$LIC" LICENSE
"$KGB" gpl.kgb LICENSE > g.log 2>&1 && rc=0 || rc=$?
check "kgb default-level compress exits 0" "$rc" 0 g.log
check "gpl.kgb checksum matches upstream" "$(md5of gpl.kgb)" "86369edb8ca943089b5691f1e4ddfd81"

# 8. round-trip the LICENSE through the archive
SUM_LIC=$(md5of LICENSE)
rm -f LICENSE
"$KGB" gpl.kgb > gx.log 2>&1 && rc=0 || rc=$?
check "extracted LICENSE matches the source" "$(md5of LICENSE)" "$SUM_LIC"

echo "KGB_CHECK_SUMMARY checks=$checks fails=$fails"
[ "$fails" -eq 0 ]
