#!/bin/sh
set -eu

programs="bin2ecm ecm2bin bincomp brrrip byteshuf cdpatch fakecrc hax65816 pecompat rels screamf uips vb2rip wordadd"
test_root="${TMPDIR:-.}/cmdpack-test-$$"
mkdir -p "$test_root"
trap 'rm -rf "$test_root"' 0 HUP INT TERM
cd "$test_root"

# Every packaged entry point must execute and report the pinned upstream version.
for program in $programs; do
    set +e
    "$program" > command-output.txt 2>&1
    command_status=$?
    set -e
    if [ "$command_status" -ne 1 ]; then
        echo "unexpected no-argument exit code for $program: $command_status" >&2
        exit 1
    fi
    grep -F "Command-Line Pack v1.06" command-output.txt >/dev/null
done

# byteshuf must losslessly split and reconstruct interleaved data.
printf '0123456789abcdef' > bytes.bin
byteshuf -u bytes.bin even.bin odd.bin
byteshuf -s rebuilt.bin even.bin odd.bin
cmp bytes.bin rebuilt.bin

# uips must create and apply a patch that reproduces the target byte-for-byte.
printf 'abcdef' > source.bin
printf 'abcXef' > target.bin
uips c delta.ips source.bin target.bin
cp source.bin patched.bin
uips a delta.ips patched.bin
cmp target.bin patched.bin

# HarmonyOS/HMDFS-specific packaging test: ecm2bin must be a materialized
# executable instead of the upstream install target's symbolic link, and the
# entry point must still select decode mode from argv[0].
ecm2bin_path=$(command -v ecm2bin)
if [ -L "$ecm2bin_path" ]; then
    echo "ecm2bin must not be a symbolic link on HarmonyOS/HMDFS" >&2
    exit 1
fi

# bin2ecm/ecm2bin must round-trip a complete 2352-byte CD sector.
dd if=/dev/zero of=disc.bin bs=2352 count=1 2>/dev/null
bin2ecm disc.bin disc.ecm
ecm2bin disc.ecm disc.out
cmp disc.bin disc.out

# Exercise four additional utilities on deterministic inputs.
fakecrc source.bin > fakecrc.out
grep '0x[0-9A-F][0-9A-F]*' fakecrc.out >/dev/null

printf '\251\001\140' > code.bin
hax65816 code.bin 0 8000 3 > hax65816.out
grep -F 'lda #$01' hax65816.out >/dev/null

rels 135 bytes.bin > rels.out
grep -F 'matches found' rels.out >/dev/null

wordadd A B C > wordadd.out
grep -F '1 + 2 = 3' wordadd.out >/dev/null
