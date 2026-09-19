#!/data/service/hnp/bin/bash
# test_package/test.sh - verify the i686-elf cross-compiler end to end (R34).
# Runs in the conanrun env, so PATH contains the installed bin/ of both
# i686-elf-gcc and the i686-elf-binutils dependency.
set -euo pipefail

echo "[test] i686-elf-gcc --version"
i686-elf-gcc --version | head -1

echo "[test] i686-elf-g++ --version"
i686-elf-g++ --version | head -1

echo "[test] i686-elf-gcc: compile test.c -> test.o"
i686-elf-gcc -O2 -c -o test.o test.c

echo "[test] i686-elf-readelf: object machine is Intel 80386"
i686-elf-readelf -h test.o | grep -Eqi "Intel 80386"

echo "[test] i686-elf-objdump: disassembly contains _start"
i686-elf-objdump -d test.o | grep -q "_start"

cat > link.ld <<'LD'
ENTRY(_start)
SECTIONS
{
    . = 0x1000;
    .text : { *(.text) }
    .data : { *(.data) }
    .bss  : { *(.bss) }
}
LD

echo "[test] i686-elf-gcc: link freestanding ELF (-nostdlib)"
i686-elf-gcc -nostdlib -T link.ld -o test.elf test.o

echo "[test] i686-elf-readelf: linked ELF machine is Intel 80386"
i686-elf-readelf -h test.elf | grep -Eqi "Intel 80386"

echo "PASS: i686-elf-gcc cross-compiler functional"
