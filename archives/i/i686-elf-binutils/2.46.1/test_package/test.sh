#!/data/service/hnp/bin/bash
# test_package/test.sh - verify the i686-elf cross-binutils toolchain (R34).
# Runs in the conanrun env, so PATH contains the installed bin/ with the
# i686-elf-* tools.
set -euo pipefail

echo "[test] i686-elf-as --version"
i686-elf-as --version | head -1

# Assemble a minimal i686-elf program: exit with code 42 via int 0x80.
cat > test.s <<'ASM'
	.text
	.globl _start
_start:
	movl $1, %eax      # sys_exit (i386)
	movl $42, %ebx     # exit code 42
	int $0x80
ASM
echo "[test] i686-elf-as: assemble test.s -> test.o"
i686-elf-as -o test.o test.s

echo "[test] i686-elf-readelf: confirm machine is Intel 80386"
i686-elf-readelf -h test.o | grep -Eqi "Intel 80386"

echo "[test] i686-elf-objdump: disassemble and find int 0x80"
i686-elf-objdump -d test.o | grep -q "int.*0x80"

echo "[test] i686-elf-ar: archive test.o into libtest.a"
i686-elf-ar rcs libtest.a test.o
i686-elf-ar t libtest.a | grep -q "test.o"

echo "[test] i686-elf-nm: list symbol _start"
i686-elf-nm test.o | grep -q "_start"

echo "PASS: i686-elf-binutils cross-toolchain tools functional"
