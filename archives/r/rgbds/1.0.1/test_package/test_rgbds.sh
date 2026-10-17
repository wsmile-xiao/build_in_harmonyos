#!/usr/bin/env bash
# test_package/test_rgbds.sh — functional consumer test for rgbds.
# Invokes the four packaged binaries by absolute path (passed as the single
# argument: the package bin/ directory) so that moving bin/ in the destructive
# negative test proves this test depends on the packaged artifacts.
set -eu

BIN_DIR="${1:?usage: test_rgbds.sh <bin-dir>}"
RGBASM="$BIN_DIR/rgbasm"
RGBLINK="$BIN_DIR/rgblink"
RGBFIX="$BIN_DIR/rgbfix"
RGBGFX="$BIN_DIR/rgbgfx"

for tool in "$RGBASM" "$RGBLINK" "$RGBFIX" "$RGBGFX"; do
    if [ ! -x "$tool" ]; then
        echo "rgbds binary not found: $tool" >&2
        exit 127
    fi
done

workdir="${TMPDIR:-${HOME:-/data/service/hnp}}/rgbds-test-$$"
trap 'rm -rf "$workdir"' EXIT
mkdir -p "$workdir"

# 1. Version smoke test. rgbgfx --version additionally proves the libpng
#    dependency is present and loadable (rgbgfx links libpng).
for tool in "$RGBASM" "$RGBLINK" "$RGBFIX" "$RGBGFX"; do
    "$tool" --version | grep -F "v1.0.1" > /dev/null
done

# 2. End-to-end toolchain: assemble -> link -> fix a minimal Game Boy ROM.
cat > "$workdir/test.asm" <<'ASM'
SECTION "Header", ROM0[$100]
    jp EntryPoint

SECTION "Main", ROM0[$150]
EntryPoint:
    ld a, 42
    ret
ASM

"$RGBASM" -o "$workdir/test.o" "$workdir/test.asm"
[ -s "$workdir/test.o" ]

"$RGBLINK" -o "$workdir/test.gb" "$workdir/test.o"
[ -s "$workdir/test.gb" ]

# rgblink pads to one 16 KiB ROM bank (0x4000) for a minimal program.
size=$(wc -c < "$workdir/test.gb" | tr -d '[:space:]')
[ "$size" -ge 16384 ]

"$RGBFIX" -v "$workdir/test.gb"

echo "rgbds functional assertions passed"
