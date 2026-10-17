#!/data/service/hnp/bin/bash
# test_package/test.sh — headless emulation test for the nestopia binary.
# Called by test_package/conanfile.py test() method.
#
# Verifies:
#   1. The binary exists and is a non-empty ELF for aarch64
#   2. `nestopia --version` reports the expected version string
#   3. `nestopia --frames 120 <rom>` runs the emulator core (CPU/PPU/APU)
#      for 120 frames headless on a generated minimal NROM ROM
#
# The ROM is generated inline (16-byte iNES header + 16KB PRG with a
# 3-instruction loop + vectors, + 8KB CHR) so no binary fixture is
# committed to the repo.
set -eu

BIN="${1:?usage: test.sh <nestopia-binary>}"
DATADIR="${2:?usage: test.sh <nestopia-binary> <data-dir>}"
WORK="${3:?usage: test.sh <nestopia-binary> <data-dir> <work-dir>}"

# --- Test 1: binary exists and is non-empty ---
if [ ! -s "$BIN" ]; then
    echo "FAIL: nestopia binary not found or empty: $BIN"
    exit 1
fi

# --- Test 2: ELF magic + 64-bit + AArch64 ---
elf_magic=$(od -A n -t x1 -N 4 "$BIN" | tr -d " \n")
if [ "$elf_magic" != "7f454c46" ]; then
    echo "FAIL: nestopia is not an ELF file (magic: $elf_magic)"
    exit 1
fi
elf_class=$(od -A n -t x1 -j 4 -N 1 "$BIN" | tr -d " \n")
if [ "$elf_class" != "02" ]; then
    echo "FAIL: nestopia ELF class is not 64-bit (got $elf_class)"
    exit 1
fi
e_machine=$(od -A n -t x1 -j 18 -N 2 "$BIN" | tr -d " \n")
if [ "$e_machine" != "b700" ]; then
    echo "FAIL: nestopia ELF machine is not AARCH64 (got $e_machine)"
    exit 1
fi

# --- Test 3: --version smoke ---
OUT=$("$BIN" --version 2>&1) || true
echo "$OUT" | head -2
case "$OUT" in
    *"Nestopia UE 1.53.2"*) echo "PASS: --version OK" ;;
    *) echo "FAIL: unexpected --version output: $OUT"; exit 1 ;;
esac

# --- Test 4: generate minimal NROM ROM and run 120 frames headless ---
ROM="$WORK/test_rom.nes"
python3 - "$ROM" <<'PYEOF'
import sys
# Minimal iNES NROM ROM: header + 16KB PRG (3-instruction loop, vectors
# at $FFFA-$FFFF -> $8000) + 8KB CHR
prg = bytearray(16 * 1024)
prg[0] = 0xA9  # LDA #imm
prg[1] = 0x42
prg[2] = 0x85  # STA zp
prg[3] = 0x00
prg[4] = 0x4C  # JMP abs
prg[5] = 0x00
prg[6] = 0x80
prg[0x3FFA] = 0x00; prg[0x3FFB] = 0x80  # NMI
prg[0x3FFC] = 0x00; prg[0x3FFD] = 0x80  # RESET
prg[0x3FFE] = 0x00; prg[0x3FFF] = 0x80  # IRQ
chr_ = bytearray(8 * 1024)
header = bytearray(16)
header[0:4] = b"NES\x1a"
header[4] = 1
header[5] = 1
header[6] = 0x01
with open(sys.argv[1], "wb") as f:
    f.write(bytes(header) + bytes(prg) + bytes(chr_))
PYEOF

# The emulator looks up NstDatabase.xml in $PWD — run from the package
# data directory.
cd "$DATADIR"
OUT=$("$BIN" --frames 120 "$ROM" 2>&1) || true
echo "$OUT" | head -3
case "$OUT" in
    *"Executed 120 frames"*) echo "PASS: headless emulation (120 frames) OK" ;;
    *) echo "FAIL: --frames 120 output: $OUT"; exit 1 ;;
esac

# cleanup
rm -f "$ROM"
echo "ALL TESTS PASSED"
