#!/bin/sh
#--------------------------------------------------------------------
# Consumer test for isight-firmware-tools 1.6-4.3 (installed programs).
#
# Env:
#   IFT_EXTRACT  path to the installed ift-extract executable
#   IFT_EXPORT   path to the installed ift-export executable
#   IFT_LOAD     path to the installed ift-load executable
# Exit: 0 = all checks passed, 1 = failure
#--------------------------------------------------------------------
set -eu

IFT_EXTRACT="${IFT_EXTRACT:?IFT_EXTRACT must point to ift-extract}"
IFT_EXPORT="${IFT_EXPORT:?IFT_EXPORT must point to ift-export}"
IFT_LOAD="${IFT_LOAD:?IFT_LOAD must point to ift-load}"

WORK="${TMPDIR:-.}/isight-test.$$"
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

nonzero() { if [ "$1" -ne 0 ]; then echo nonzero; else echo zero; fi; }

# 1-2. ift-extract --help
"$IFT_EXTRACT" --help > e.out 2> e.err && rc=0 || rc=$?
check "ift-extract --help exits 0" "$rc" 0 e.err
check "ift-extract --help prints usage" "$(grep -c -i -F 'Usage' e.out)" 1

# 3-4. ift-extract without -a
"$IFT_EXTRACT" > a.out 2> a.err && rc=0 || rc=$?
check "ift-extract (no -a) exits 1" "$rc" 1
check "ift-extract requires -a" "$(grep -c -F 'Option -a is mandatory' a.err)" 1

# 5. ift-extract with a missing driver aborts (g_error)
"$IFT_EXTRACT" -a ./no-such-driver -d "$WORK" -f x.fw > d.out 2> d.err && rc=0 || rc=$?
check "ift-extract (missing driver) fails" "$(nonzero "$rc")" nonzero

# 6-7. ift-export --help
"$IFT_EXPORT" --help > pe.out 2> pe.err && rc=0 || rc=$?
check "ift-export --help exits 0" "$rc" 0 pe.err
check "ift-export --help prints usage" "$(grep -c -i -F 'Usage' pe.out)" 1

# 8. ift-export with a missing input aborts
"$IFT_EXPORT" -i ./no-such-firmware -o out.ihx > x.out 2> x.err && rc=0 || rc=$?
check "ift-export (missing input) fails" "$(nonzero "$rc")" nonzero

# 9-11. real Intel HEX conversion of a synthetic firmware image:
#   len=4, request address=0x0000, 4 data bytes 'ABCD' -> :0400000041424344F2
printf '\000\004\000\000ABCD' > fw.bin
"$IFT_EXPORT" -i fw.bin -o fw.ihx > c.out 2> c.err && rc=0 || rc=$?
check "ift-export converts synthetic firmware" "$rc" 0 c.err
check "ift-export emits the data record" "$(grep -c -F ':0400000041424344F2' fw.ihx)" 1
check "ift-export emits the EOF record" "$(grep -c -F ':00000001FF' fw.ihx)" 1

# 12-13. ift-load --help and missing-firmware path
"$IFT_LOAD" --help > l.out 2> l.err && rc=0 || rc=$?
check "ift-load --help exits 0" "$rc" 0 l.err
"$IFT_LOAD" > m.out 2> m.err && rc=0 || rc=$?
check "ift-load (missing firmware) fails" "$(nonzero "$rc")" nonzero

echo "ISIGHT_CHECK_SUMMARY checks=$checks fails=$fails"
[ "$fails" -eq 0 ]
