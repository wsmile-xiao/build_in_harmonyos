#!/bin/sh
#--------------------------------------------------------------------
# Consumer test for ree 1.4.1 (installed ree / fontdump).
#
# fontdump is tested on a synthetic ROM image that contains one valid 8x8 VGA
# font block; ree is run and must terminate with a known banner.
#
# Env:
#   REE_BIN       path to the installed ree executable
#   FONTDUMP_BIN  path to the installed fontdump executable
# Exit: 0 = all checks passed, 1 = failure
#--------------------------------------------------------------------
set -eu

REE="${REE_BIN:?REE_BIN must point to the installed ree executable}"
FONTD="${FONTDUMP_BIN:?FONTDUMP_BIN must point to the installed fontdump executable}"

WORK="${TMPDIR:-.}/ree-test.$$"
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

# 1-2. fontdump without arguments prints its syntax and fails
"$FONTD" > fd_usage.out 2>&1 && rc=0 || rc=$?
check "fontdump without arguments exits 1" "$rc" 1
check "fontdump prints its syntax" "$(grep -c -F 'Syntax: fontdump' fd_usage.out)" 1

# Build a 2048-byte ROM image holding one valid 8x8 font:
#   char 0 and char 255 are 8 zero bytes (the FONT8 signature),
#   char 32 is all zero (checksum 0), char 65 ('A') is non-zero.
head -c 520 /dev/zero > rom.bin
printf '\001\001\001\001\001\001\001\001' >> rom.bin
head -c 1520 /dev/zero >> rom.bin

# 3-7. fontdump extracts it
"$FONTD" rom.bin > fd.out 2>&1 && rc=0 || rc=$?
check "fontdump scans the ROM" "$rc" 0 fd.out
check "fontdump reports the size" "$(grep -c -F 'size 2048' fd.out)" 1
check "fontdump finds the FONT8" "$(grep -c -F 'Found FONT8' fd.out)" 1
check "fontdump wrote 8x8.fnt" "$([ -f 8x8.fnt ] && echo 0 || echo 1)" 0
check "8x8.fnt is byte-identical to the ROM block" "$(md5of 8x8.fnt)" "$(md5of rom.bin)"

# 8-9. ree runs and terminates with a known banner (it needs /dev/mem read
# access, which a normal OHOS process does not have)
"$REE" > ree.out 2>&1 && rc=0 || rc=$?
check "ree terminates with 0 or 1" "$([ "$rc" -eq 0 ] || [ "$rc" -eq 1 ] && echo 0 || echo 1)" 0
check "ree prints a known banner" \
	"$(grep -q -E 'could not open /dev/mem|scanning' ree.out && echo 0 || echo 1)" 0

echo "REE_CHECK_SUMMARY checks=$checks fails=$fails"
[ "$fails" -eq 0 ]
