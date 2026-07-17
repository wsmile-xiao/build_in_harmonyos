#!/data/service/hnp/bin/bash
# test_package/test.sh — verify the x86_64-elf cross-binutils toolchain (R34).
# Runs in the conanrun env, so PATH contains the installed bin/ with the
# x86_64-elf-* tools.
set -euo pipefail

echo "[test] x86_64-elf-as --version"
x86_64-elf-as --version | head -1

# Assemble a minimal x86_64-elf program: exit with code 42 via sys_exit.
cat > test.s <<'ASM'
	.text
	.globl _start
_start:
	movq $60, %rax      # sys_exit
	movq $42, %rdi      # exit code 42
	syscall
ASM

echo "[test] x86_64-elf-as: assemble test.s -> test.o"
x86_64-elf-as -o test.o test.s

echo "[test] x86_64-elf-readelf: confirm machine is x86-64"
x86_64-elf-readelf -h test.o | grep -Eqi 'Machine:.*(Advanced Micro Devices|X86-64|x86-64)'

echo "[test] x86_64-elf-objdump: disassemble and find syscall"
x86_64-elf-objdump -d test.o | grep -q 'syscall'

echo "[test] x86_64-elf-ar: archive test.o into libtest.a"
x86_64-elf-ar rcs libtest.a test.o
x86_64-elf-ar t libtest.a | grep -q 'test.o'

echo "[test] x86_64-elf-nm: list symbol _start"
x86_64-elf-nm test.o | grep -q '_start'

echo "PASS: x86_64-elf-binutils cross-toolchain tools functional"
