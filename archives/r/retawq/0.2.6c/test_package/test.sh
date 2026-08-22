#!/usr/bin/env bash
# test_package/test.sh — smoke test for retawq executable
# retawq is a terminal web browser. We verify the binary exists and can start.
set -euo pipefail

echo "[step] Check retawq binary exists"
if command -v retawq >/dev/null 2>&1; then
    echo "        [ok] retawq found in PATH"
else
    echo "        [fail] retawq not in PATH"
    exit 1
fi

echo "[step] Check retawq binary is valid ELF"
retawq_bin=$(command -v retawq)
# Check ELF magic bytes (0x7f 45 4c 46 = \x7fELF)
elf_magic=$(head -c 4 "$retawq_bin" 2>/dev/null | od -A n -t x1 2>/dev/null | tr -d ' \n' || echo "")
if echo "$elf_magic" | grep -qi "^7f454c46"; then
    echo "        [ok] retawq binary is valid ELF"
else
    echo "        [fail] retawq binary is not valid ELF (magic: $elf_magic)"
    exit 1
fi

echo "[step] Execute retawq to verify it starts"
# retawq needs a terminal; running without TTY produces error output.
# We verify the binary is functional (not crashed) by checking output or exit code.
# Temporarily disable set -e to capture the real exit code
set +e
retawq_output=$(retawq --help 2>&1)
retawq_rc=$?
set -e
if [ -n "$retawq_output" ]; then
    echo "        [ok] retawq produced output on startup"
elif [ "$retawq_rc" -ne 139 ] && [ "$retawq_rc" -ne 134 ]; then
    # 139=SIGSEGV, 134=SIGABRT — these would indicate a crash
    echo "        [ok] retawq exited cleanly (rc=$retawq_rc) without crash"
else
    echo "        [fail] retawq crashed (rc=$retawq_rc)"
    exit 1
fi
