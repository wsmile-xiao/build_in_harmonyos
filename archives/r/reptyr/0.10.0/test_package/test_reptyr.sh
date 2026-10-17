#!/bin/sh
# test_reptyr.sh — consumer-side regression tests for the packaged reptyr CLI.
#
# The upstream suite (test/basic.py, test/tty-steal.py) drives the ptrace
# attach path end-to-end with pexpect on a real terminal.  PTRACE_ATTACH is
# refused with EPERM for unprivileged processes on HarmonyOS (the process is
# seccomp-filtered; PTRACE_TRACEME and process_vm_readv fail the same way —
# see reports/test-report.md), so this consumer suite verifies everything the
# installed binary can still do on such platforms:
#   * installed on PATH; -v / -h output and exit codes
#   * argument validation (missing pid, non-numeric pid, unknown option)
#   * attach error reporting for a pid that cannot exist
#   * -l: allocate a new pty pair and announce its slave path
#   * -L: run a command with its stdio on the pty slave, export REPTYR_PTY and
#     relay the child's stdout
#
# Every check emits exactly one TAP line; assertion_count in MANIFEST.yml is
# the number of TAP lines this script emits (18).

set -u

workdir="${TMPDIR:-/tmp}/reptyr-test-$$"
mkdir -p "$workdir" || exit 1
trap 'rm -rf "$workdir"' EXIT HUP INT TERM

passed=0
failed=0

check() {
    # check <description> <expected> <actual>
    desc=$1 expected=$2 actual=$3
    if [ "$actual" = "$expected" ]; then
        passed=$((passed + 1))
        echo "ok - $desc"
    else
        failed=$((failed + 1))
        echo "not ok - $desc (expected: $expected, actual: $actual)"
    fi
}

contains() {
    # contains <description> <needle> <file>
    desc=$1 needle=$2 file=$3
    if grep -q -- "$needle" "$file" 2>/dev/null; then
        passed=$((passed + 1))
        echo "ok - $desc"
    else
        failed=$((failed + 1))
        echo "not ok - $desc (missing: $needle)"
    fi
}

echo "1..18"

# 1. the binary must be on PATH (installed into bin/ and exported by the package)
if command -v reptyr >/dev/null 2>&1; then
    check "reptyr binary is installed and on PATH" "0" "0"
else
    check "reptyr binary is installed and on PATH" "0" "1"
fi

# 2-3. version banner
reptyr -v > "$workdir/v.txt" 2>&1
check "reptyr -v exits 0" "0" "$?"
contains "reptyr -v prints the version banner" "This is reptyr version 0.10.0" "$workdir/v.txt"

# 4-5. help text
reptyr -h > "$workdir/h.txt" 2>&1
check "reptyr -h exits 0" "0" "$?"
contains "reptyr -h documents the attach usage" "reptyr \[-s\] PID" "$workdir/h.txt"

# 6-7. missing pid argument
reptyr > "$workdir/noargs.txt" 2>&1
check "missing pid exits 1" "1" "$?"
contains "missing pid is reported" "No pid specified to attach" "$workdir/noargs.txt"

# 8-9. non-numeric pid is rejected
reptyr notanumber > "$workdir/badpid.txt" 2>&1
check "non-numeric pid exits 1" "1" "$?"
contains "non-numeric pid is rejected" "Invalid pid: must be integer" "$workdir/badpid.txt"

# 10-11. attach error path for a pid that cannot exist
reptyr 999999999 > "$workdir/noproc.txt" 2>&1
check "non-existent pid exits 1" "1" "$?"
contains "non-existent pid reports No such process" "No such process" "$workdir/noproc.txt"

# 12-13. unknown option
reptyr -Z > "$workdir/badopt.txt" 2>&1
check "unknown option exits 1" "1" "$?"
contains "unknown option prints the usage" "Usage:" "$workdir/badopt.txt"

# 14. -l allocates a new pty pair and announces the slave path
reptyr -l < /dev/null > "$workdir/pty.txt" 2>&1 &
pty_pid=$!
i=0
while [ $i -lt 10 ] && ! grep -q "Opened a new pty:" "$workdir/pty.txt" 2>/dev/null; do
    sleep 1
    i=$((i + 1))
done
kill $pty_pid 2>/dev/null
wait $pty_pid 2>/dev/null
contains "reptyr -l announces the new pty slave" "Opened a new pty: /dev/pts/" "$workdir/pty.txt"
slave=$(sed -n 's/^Opened a new pty: \(.*\)$/\1/p' "$workdir/pty.txt" | tr -d '\r' | head -n 1)

# 15-18. -L runs a command with its stdio on the pty slave and relays stdout
(
    reptyr -L sh -c 'echo child-marker-42; echo child-pty=$REPTYR_PTY; [ -c "$REPTYR_PTY" ] && echo child-pty-is-char-device' < /dev/null > "$workdir/L.txt" 2>&1
    echo $? > "$workdir/L.rc"
) &
L_pid=$!
i=0
while [ $i -lt 15 ] && [ ! -f "$workdir/L.rc" ]; do
    sleep 1
    i=$((i + 1))
done
kill $L_pid 2>/dev/null
wait $L_pid 2>/dev/null
contains "reptyr -L announces the new pty slave" "Opened a new pty: /dev/pts/" "$workdir/L.txt"
contains "reptyr -L relays the child's stdout" "child-marker-42" "$workdir/L.txt"
contains "the child's REPTYR_PTY points at a character device" "child-pty-is-char-device" "$workdir/L.txt"
# note: the child's stdout goes through a pty, so the line discipline adds CR
# before LF (ONLCR); strip it before comparing.
child_slave=$(sed -n 's/^.*child-pty=\(.*\)$/\1/p' "$workdir/L.txt" | tr -d '\r' | head -n 1)
if [ -n "$slave" ] && [ "$slave" = "$child_slave" ]; then
    check "REPTYR_PTY equals the announced pty slave" "$slave" "$child_slave"
else
    check "REPTYR_PTY equals the announced pty slave" "$slave" "$child_slave (announced=$slave)"
fi

echo "# passed: $passed, failed: $failed"
if [ "$failed" -ne 0 ]; then
    exit 1
fi
exit 0
