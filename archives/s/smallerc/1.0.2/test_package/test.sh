#!/usr/bin/env bash
set -euo pipefail

script_dir="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
test_root="${TMPDIR:-.}/smallerc-test-$$"

mkdir -p "$test_root"
trap 'rm -rf "$test_root"' EXIT HUP INT TERM

for command_name in smlrc smlrl smlrcc smlrpp n2f nasm; do
  command -v "$command_name" >/dev/null
done

test -n "${SMLRC:-}"
test -f "$SMLRC/include/limits.h"
test -f "$SMLRC/lib/lcdh.a"
nasm -v | grep -F "NASM version 2.16.03"

cp "$script_dir/test.c" "$test_root/test.c"
cd "$test_root"

# Exercise preprocessing and code generation without invoking the assembler.
smlrcc -v -linux -c -S test.c -o test.asm
test -s test.asm

# Exercise the full preprocessor/compiler/assembler/linker pipeline. The
# generated DOS executable is inspected rather than run on the OHOS host.
smlrcc -v -dosh test.c -o test.exe
test -s test.exe
test "$(dd if=test.exe bs=2 count=1 2>/dev/null)" = "MZ"
