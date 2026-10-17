#!/bin/sh
# Execute a 32-bit ARM program under this package's qemu-arm.
#
# This is the decisive check for the package: the host is aarch64 and has no
# AArch32 compatibility layer, so an ARM binary can only run through the
# emulator.  Assembling and linking it with the cross binutils and then seeing
# its output come back is positive proof that the packaged user-mode emulator
# actually works, not merely that its --version flag responds.
#
# Kept as a standalone script (rather than inline in conanfile.py) so the same
# probe can be re-run by hand against any build, and because the CI quality
# gate expects a test source alongside the recipe.
#
# Usage: run_arm_probe.sh <binutils-bin-dir> <qemu-bin-dir> [work-dir]
# Exit:  0 on success, 1 on any failed step.
set -u

if [ $# -lt 2 ]; then
    echo "usage: $0 <binutils-bin-dir> <qemu-bin-dir> [work-dir]" >&2
    exit 2
fi

BINUTILS_DIR=$1
QEMU_DIR=$2
WORK=${3:-${TMPDIR:-/tmp}}

HERE=$(cd "$(dirname "$0")" && pwd)
AS="$BINUTILS_DIR/arm-none-eabi-as"
LD="$BINUTILS_DIR/arm-none-eabi-ld"
READELF="$BINUTILS_DIR/arm-none-eabi-readelf"
QEMU_ARM="$QEMU_DIR/qemu-arm"
QEMU_AARCH64="$QEMU_DIR/qemu-aarch64"

for tool in "$AS" "$LD" "$QEMU_ARM"; do
    if [ ! -x "$tool" ]; then
        echo "missing required tool: $tool" >&2
        exit 1
    fi
done

WORK=$(mktemp -d "$WORK/arm-probe.XXXXXX") || exit 1
trap 'rm -rf "$WORK"' EXIT INT TERM

OBJ=$WORK/hello_arm.o
ELF=$WORK/hello_arm.elf

echo "== assembling hello_arm.s with $AS"
"$AS" -o "$OBJ" "$HERE/hello_arm.s" || exit 1

echo "== linking a static ARM ELF with $LD"
"$LD" -static -e _start -o "$ELF" "$OBJ" || exit 1

if [ -x "$READELF" ]; then
    echo "== linked image"
    "$READELF" -h "$ELF" | grep -E 'Class|Machine|Type' || true
fi

echo "== running the ARM binary under $QEMU_ARM"
output=$("$QEMU_ARM" "$ELF" 2>&1)
status=$?
echo "$output"
if [ "$status" -ne 0 ]; then
    echo "FAIL: qemu-arm exited with $status" >&2
    exit 1
fi
case "$output" in
    *qemu-arm-ok*) ;;
    *)
        echo "FAIL: expected 'qemu-arm-ok' in the output" >&2
        exit 1
        ;;
esac

# Negative control: the AArch64 user-mode emulator must refuse a 32-bit ARM
# image rather than silently mis-handle it.
if [ -x "$QEMU_AARCH64" ]; then
    echo "== negative control: $QEMU_AARCH64 must reject the 32-bit binary"
    control=$("$QEMU_AARCH64" "$ELF" 2>&1 || true)
    case "$control" in
        *qemu-arm-ok*)
            echo "FAIL: qemu-aarch64 ran a 32-bit ARM binary" >&2
            exit 1
            ;;
        *) echo "   rejected as expected" ;;
    esac
fi

echo "PASS: the packaged qemu-arm executed the ARM program"
exit 0
