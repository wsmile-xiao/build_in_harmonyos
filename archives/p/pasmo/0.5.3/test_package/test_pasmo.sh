#!/bin/sh
# test_pasmo.sh — consumer-side regression tests for the packaged pasmo CLI.
#
# Upstream 0.5.3 ships no test suite: there is no tests/ tree, Makefile.am
# declares only `bin_PROGRAMS = pasmo` (no TESTS/check_PROGRAMS/check-local)
# and `make check` executes zero cases ("Nothing to be done for 'check'").
# These assertions exercise the documented behaviour of the installed
# assembler so a broken package cannot pass:
#   * raw binary / Intel HEX output with byte-level comparison
#   * the Spectrum TAP/TZX/+3DOS, Amsdos and MSX container writers
#   * CP/M 86 CMD output and the --86 8086 backend
#   * diagnostics, exit codes, --err, INCLUDE (-I), --nocase, --bracket
#
# Every check emits exactly one TAP line; assertion_count in MANIFEST.yml is
# the number of TAP lines this script emits (22).
#
# NOTE: deliberately not `set -e`: several assertions inspect commands that
# return non-zero on purpose (bad source -> exit 1) and check() evaluates
# them as conditions.
set -u

DIR="${TMPDIR:-/tmp}/pasmo-test.$$"
mkdir -p "$DIR" || exit 1
cd "$DIR" || exit 1

n_ok=0
n_fail=0
check() {
  msg="$1"
  shift
  if eval "$@" >/dev/null 2>&1; then
    echo "ok - $msg"
    n_ok=$((n_ok + 1))
  else
    echo "not ok - $msg"
    n_fail=$((n_fail + 1))
  fi
}

hex_of() {
  od -An -tx1 "$1" | tr -d ' \n'
}

echo "1..22"

# ---- fixtures --------------------------------------------------------------

cat > t.asm <<'EOF'
	org 100h
start:	ld a, 42
	ld (200h), a
	jp start
EOF

cat > prog2.asm <<'EOF'
	org 4000h
main:	ld hl, 2000h
	ld de, 1234h
	ld bc, 5678h
	xor a
	ld (hl), a
	inc hl
	call main
	jp main
	halt
EOF

cat > io.asm <<'EOF'
	org 100h
	in a,(2)
	out (1),a
EOF

cat > bad.asm <<'EOF'
	org 100h
	jp nowhere
EOF

cat > br.asm <<'EOF'
	org 100h
	ld a,[hl]
	ld [hl],a
EOF

cat > case.asm <<'EOF'
	org 100h
	Label1:	nop
	jp label1
EOF

cat > main.asm <<'EOF'
	org 100h
	include "inc.asm"
EOF
printf '\tnop\n' > inc.asm

# expected image of t.asm: ld a,42 | ld (200h),a | jp 100h
CODE_T="3e2a320002c30001"

# 1. the binary is installed and exported through the package runenv (PATH)
check "pasmo binary is installed and on PATH" 'command -v pasmo'

# 2. no arguments: version banner + usage, non-zero exit
check "no-argument usage prints the 0.5.3 banner and fails" \
  'pasmo </dev/null 2>&1 | grep -q "Pasmo v. 0.5.3" && ! pasmo </dev/null >/dev/null 2>&1'

# 3. --bin produces the exact raw image
check "assembles a raw binary byte-for-byte" \
  'pasmo --bin t.asm t.bin </dev/null && [ "$(hex_of t.bin)" = "'"$CODE_T"'" ]'

# 4. no format option defaults to the same raw image
check "default output format is raw binary" \
  'pasmo t.asm d.bin </dev/null && [ "$(hex_of d.bin)" = "'"$CODE_T"'" ]'

# 5. --hex produces the exact Intel HEX records (incl. checksums, CRLF eol)
check "emits Intel HEX with correct checksums" \
  'pasmo --hex t.asm t.hex </dev/null && printf ":080100003E2A320002C3000197\r\n:00000001FF\r\n" > exp.hex && cmp -s t.hex exp.hex'

# 6. multi-instruction program, hand-verified Z80 opcodes
check "assembles a multi-instruction program with exact opcodes" \
  'pasmo --bin prog2.asm prog2.bin </dev/null && [ "$(hex_of prog2.bin)" = "210020113412017856af7723cd0040c3004076" ]'

# 7. IN/OUT fixed-port encodings
check "encodes IN/OUT fixed-port instructions" \
  'pasmo --bin io.asm io.bin </dev/null && [ "$(hex_of io.bin)" = "db02d301" ]'

# 8. undefined symbol: diagnostic on stderr + non-zero exit (0.5.3 exit fix)
check "undefined symbol fails with a diagnostic on stderr" \
  'pasmo --bin bad.asm bad.bin </dev/null >bad.out 2>bad.err; [ $? -ne 0 ] && grep -q "is undefined" bad.err'

# 9. --err routes the diagnostic to stdout
check "--err routes the diagnostic to stdout" \
  'pasmo --err --bin bad.asm bad2.bin </dev/null >err.out 2>err.err; [ $? -ne 0 ] && grep -q "is undefined" err.out'

# 10. INCLUDE resolution via -I
check "resolves INCLUDE files via -I" \
  'pasmo -I . --bin main.asm main.bin </dev/null && [ "$(hex_of main.bin)" = "00" ]'

# 11. symbol listing (third positional argument)
check "writes the symbol listing with the start address" \
  'pasmo t.asm t.bin t.sym </dev/null && grep -q "start" t.sym && grep -q "EQU 00100H" t.sym'

# 12. --nocase resolves case-mismatched labels
check "--nocase resolves case-mismatched labels" \
  'pasmo --nocase --bin case.asm case.bin </dev/null && [ "$(hex_of case.bin)" = "00c30001" ]'

# 13. --bracket indirection syntax
check "--bracket accepts bracket indirection" \
  'pasmo --bracket --bin br.asm br.bin </dev/null && [ "$(hex_of br.bin)" = "7e77" ]'

# 14. Spectrum TAP: exact 33-byte image (header + data block, both checksums)
check "--tap writes the exact Spectrum tape image" \
  'pasmo --tap --name TEST t.asm out.tap </dev/null && [ "$(hex_of out.tap)" = "13000003544553542020202020200800000100809c0a00ff3e2a320002c3000119" ]'

# 15. TZX container: exact 49-byte image (magic + both blocks)
check "--tzx writes the exact ZXTape! container" \
  'pasmo --tzx t.asm out.tzx </dev/null && [ "$(hex_of out.tzx)" = "5a5854617065211a010d10e803130000036f75742e747a782020200800000100809c10e8030a00ff3e2a320002c3000119" ]'

# 16. +3DOS: magic + 256-byte image + code at offset 128
check "--plus3dos writes a PLUS3DOS image with code at offset 128" \
  'pasmo --plus3dos t.asm out.p3d </dev/null && [ "$(dd if=out.p3d bs=1 count=9 2>/dev/null | od -An -tx1 | tr -d " \n")" = "504c555333444f531a" ] && [ "$(wc -c < out.p3d | tr -d " ")" = "256" ] && [ "$(dd if=out.p3d bs=1 skip=128 count=8 2>/dev/null | od -An -tx1 | tr -d " \n")" = "'"$CODE_T"'" ]'

# 17. --tapbas: 109-byte image, BASIC "loader" block first, code block last
check "--tapbas prepends the BASIC loader block" \
  'pasmo --tapbas t.asm out.tapbas </dev/null && [ "$(wc -c < out.tapbas | tr -d " ")" = "109" ] && [ "$(dd if=out.tapbas bs=1 count=16 2>/dev/null | od -An -tx1 | tr -d " \n")" = "130000006c6f61646572202020203300" ] && [ "$(tail -c 9 out.tapbas | od -An -tx1 | tr -d " \n")" = "3e2a320002c3000119" ]'

# 18. Amsdos: 136-byte image, output filename in the 128-byte header, code last
check "--amsdos writes the Amsdos header with the output filename" \
  'pasmo --amsdos t.asm out.ams </dev/null && [ "$(wc -c < out.ams | tr -d " ")" = "136" ] && [ "$(dd if=out.ams bs=1 skip=1 count=7 2>/dev/null)" = "out.ams" ] && [ "$(tail -c 8 out.ams | od -An -tx1 | tr -d " \n")" = "'"$CODE_T"'" ]'

# 19. MSX: exact 15-byte BLOAD image
check "--msx writes the MSX BLOAD header and code" \
  'pasmo --msx t.asm out.msx </dev/null && [ "$(hex_of out.msx)" = "fe0001070100003e2a320002c30001" ]'

# 20. CP/M-86 CMD: 392-byte image whose payload ends with the code
check "--cmd writes a CP/M 86 .CMD image carrying the code" \
  'pasmo --cmd t.asm out.cmd </dev/null && [ "$(wc -c < out.cmd | tr -d " ")" = "392" ] && [ "$(tail -c 8 out.cmd | od -An -tx1 | tr -d " \n")" = "'"$CODE_T"'" ]'

# 21. --86: Z80 source translated to 8086 code (exact bytes)
check "--86 emits 8086 code for the same source" \
  'pasmo --86 --bin t.asm out86.bin </dev/null && [ "$(hex_of out86.bin)" = "b02aa20002e9f8ff" ]'

# 22. invalid operand combination: non-zero exit (error handling, 0.5.3 fix)
check "invalid operand combination fails with a non-zero exit" \
  'printf "\torg 100h\n\tex de,de\n" > syntax.asm; pasmo --bin syntax.asm syntax.bin </dev/null >syntax.out 2>syntax.err; [ $? -ne 0 ] && grep -q "ERROR" syntax.err'

cd ..
rm -rf "$DIR"
echo "# pasmo functional assertions: pass=$n_ok fail=$n_fail"
[ "$n_fail" -eq 0 ]
