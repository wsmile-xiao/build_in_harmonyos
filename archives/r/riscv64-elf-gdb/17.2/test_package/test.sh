#!/data/service/hnp/bin/bash
# test_package/test.sh — verify the riscv64-elf-gdb cross-debugger (R34).
# Runs in the conanrun env, so PATH contains the installed bin/ with
# riscv64-elf-gdb.
# Avoids ptrace/attach (E222): only tests version, architecture support,
# command interpreter, and ELF load + disassembly.
set -uo pipefail

pass=0
fail=0

check() {
    if [ "$1" -eq 0 ]; then
        pass=$((pass + 1))
    else
        fail=$((fail + 1))
        echo "FAIL: $2 (exit=$1)"
    fi
}

echo "[test] riscv64-elf-gdb --version"
out=$(riscv64-elf-gdb --version 2>/dev/null | head -1)
echo "$out" | grep -Eq 'GNU gdb.*17\.2'
check $? "version output"

echo "[test] riscv64-elf-gdb: set and show riscv:rv64 architecture"
out=$(riscv64-elf-gdb -batch     -ex "set architecture riscv:rv64"     -ex "show architecture" 2>/dev/null)
echo "$out" | grep -Eqi 'riscv.*rv64'
check $? "set architecture riscv:rv64"

echo "[test] riscv64-elf-gdb: maintenance print architecture"
out=$(riscv64-elf-gdb -batch     -ex "set architecture riscv:rv64"     -ex "maintenance print architecture" 2>/dev/null)
echo "$out" | grep -Eqi 'riscv|rv64'
check $? "maintenance print architecture"

echo "[test] riscv64-elf-gdb: show data-directory"
out=$(riscv64-elf-gdb -batch     -ex "show data-directory" 2>/dev/null)
echo "$out" | grep -Eq 'gdb|data'
check $? "show data-directory"

echo "[test] riscv64-elf-gdb: load + disassemble riscv64 ELF (clang cross-compiled)"
CLANG=/data/service/hnp/bin/clang
$CLANG --target=riscv64-elf -c "${TESTDIR:-.}/test.s" -o "${TESTDIR:-.}/test.o" 2>/dev/null
$CLANG --target=riscv64-elf -nostdlib -static "${TESTDIR:-.}/test.o" -o "${TESTDIR:-.}/test.elf" 2>/dev/null
out=$(riscv64-elf-gdb -batch -ex "file ${TESTDIR:-.}/test.elf" -ex "set architecture riscv:rv64" -ex "disassemble _start" 2>/dev/null)
echo "$out" | grep -Eqi 'ecall|li\s+a[0-9]|riscv'
check $? "disassemble riscv64 ELF _start"

echo "Results: ${pass} passed, ${fail} failed"
if [ "$fail" -gt 0 ]; then
    exit 1
fi
echo "PASS: riscv64-elf-gdb cross-debugger functional"
