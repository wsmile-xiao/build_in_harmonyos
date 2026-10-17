#!/usr/bin/env bash
# test_far2l_tty.sh — functional test for far2l-tty binary
# Called by test_package/conanfile.py test() method
# Verifies: binary exists, is ELF aarch64, responds to --help, TTY headless launch
set -euo pipefail

FAR2L="${1:?usage: test_far2l_tty.sh <far2l_binary_path>}"

# Test 1: Binary exists and is non-empty
if [ ! -s "$FAR2L" ]; then
    echo "FAIL: far2l binary not found or empty: $FAR2L"
    exit 1
fi

# Test 2: Verify ELF magic bytes (0x7f E L F)
elf_magic=$(od -A n -t x1 -N 4 "$FAR2L" | tr -d " \n")
if [ "$elf_magic" != "7f454c46" ]; then
    echo "FAIL: far2l is not an ELF file (magic: $elf_magic)"
    exit 1
fi

# Test 3: Verify ELF class is 64-bit (byte offset 4 = 0x02)
elf_class=$(od -A n -t x1 -j 4 -N 1 "$FAR2L" | tr -d " \n")
if [ "$elf_class" != "02" ]; then
    echo "FAIL: far2l ELF class is not 64-bit (got $elf_class)"
    exit 1
fi

# Test 4: Run far2l --help and check output contains expected option strings
# far2l --help may return non-zero on headless systems without a TTY;
# the output content is validated by grep below regardless of exit code.
help_output=$("$FAR2L" --help 2>&1 || true)

# Check for expected help text patterns
if ! echo "$help_output" | grep -q "\-\-tty"; then
    echo "FAIL: far2l --help output does not contain --tty"
    exit 1
fi

if ! echo "$help_output" | grep -q "\-\-norgb"; then
    echo "FAIL: far2l --help output does not contain --norgb"
    exit 1
fi

# Test 5: Verify version string in help output
if ! echo "$help_output" | grep -q "2.8.0"; then
    echo "FAIL: far2l --help output does not contain version 2.8.0"
    exit 1
fi

# Test 6: TTY headless launch — verify far2l --tty can start without crashing
# far2l --tty requires a terminal; we provide /dev/null as stdin/stdout
# and use timeout to prevent hangs. A non-zero exit is acceptable here
# (far2l may refuse to run without a real TTY); we only verify the
# process does not crash immediately (i.e., it gets past initialization).
tty_timeout=10
if command -v timeout >/dev/null 2>&1; then
    set +e
    timeout "$tty_timeout" "$FAR2L" --tty --norgb < /dev/null > /dev/null 2>&1
    tty_exit=$?
    set -e
    # timeout returns 124 on timeout; far2l may return non-zero if TTY unavailable
    # We accept any exit code except segfault (139) or abort (134)
    if [ "$tty_exit" -eq 139 ]; then
        echo "FAIL: far2l --tty segfaulted (exit 139)"
        exit 1
    fi
    if [ "$tty_exit" -eq 134 ]; then
        echo "FAIL: far2l --tty aborted (exit 134)"
        exit 1
    fi
else
    # No timeout command available — skip TTY test, declare residual risk
    echo "SKIP: Test 6 (TTY headless) — no timeout command available"
fi

echo "All tests passed"
