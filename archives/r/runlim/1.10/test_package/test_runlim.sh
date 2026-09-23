#!/bin/sh
# test_runlim.sh — consumer-side regression tests for the packaged runlim CLI.
#
# Upstream ships no test suite: the tarball has no tests/ tree, makefile.in
# defines only the `runlim` and `clean` targets, and configure.sh has no test
# switch — there is no upstream test to run (inventory evidence in
# MANIFEST.yml).  These assertions therefore exercise the installed binary's
# documented behaviour so a broken package cannot pass:
#   * version banner, usage text, argument error paths
#   * pass-through execution and -o/--output-file log contents
#   * runlim's own status semantics: 0 ok, 2 out of time, 3 out of memory,
#     4 child SIGSEGV, 11 child other signal; child exit codes are ignored
#   * real-time limit (-r), CPU-time limit (-t/--time-limit) — the -t case is
#     the regression test for the RLIMIT_AS unit fix (an unpatched build
#     cannot exec the child and returns 1 "execvp failed")
#   * space limit through /proc sampling (-s/--space-limit)
#   * -k signal propagation and default log target (stderr)
#
# Every check emits exactly one TAP line; assertion_count in MANIFEST.yml is
# the number of TAP lines this script emits (31).

set -u

# NOTE (code-style rule 25 / CS7): `set -euo pipefail` is intentionally NOT
# used.  The harness must observe non-zero exit codes (runlim returns
# 1/2/3/4/139) as data, so `set -e` would abort legitimate checks, and
# `pipefail` is a bashism while this script must also run under the POSIX
# /bin/sh fallback used by test_package/conanfile.py.  Commands whose failure
# is expected are guarded explicitly instead.

# No core files on the device/CI worker: the -k case ends runlim by signal.
ulimit -c 0 2>/dev/null || true

workdir="$(pwd)/runlim-test-$$"
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
    # contains <description> <grep-pattern> <file>
    desc=$1 needle=$2 file=$3
    if grep -q -- "$needle" "$file" 2>/dev/null; then
        passed=$((passed + 1))
        echo "ok - $desc"
    else
        failed=$((failed + 1))
        echo "not ok - $desc (missing: $needle)"
    fi
}

echo "1..31"

# 1-3. binary installed and version banner
if command -v runlim >/dev/null 2>&1; then
    check "runlim binary is installed and on PATH" "0" "0"
else
    check "runlim binary is installed and on PATH" "0" "1"
fi
version_out=$(runlim --version 2>&1)
check "runlim --version exits 0" "0" "$?"
check "runlim --version prints 1.10" "1.10" "$version_out"

# 4-5. usage summary
runlim -h > "$workdir/help.txt" 2>&1
check "runlim -h exits 0" "0" "$?"
contains "runlim -h prints the usage summary" "usage: runlim" "$workdir/help.txt"

# 6-11. argument error paths
runlim --badopt > "$workdir/out.txt" 2> "$workdir/err.txt"
check "invalid option exits 1" "1" "$?"
contains "invalid option is reported" "invalid option" "$workdir/err.txt"
runlim > "$workdir/out.txt" 2> "$workdir/err.txt"
check "missing program exits 1" "1" "$?"
contains "missing program is reported" "no program specified" "$workdir/err.txt"
runlim -t > "$workdir/out.txt" 2> "$workdir/err.txt"
check "missing number argument exits 1" "1" "$?"
contains "missing number argument is reported" "number argument" "$workdir/err.txt"

# 12-15. pass-through execution and log file (-o)
runlim -o "$workdir/run.log" sh -c 'echo pass-through-ok' > "$workdir/out.txt" 2> "$workdir/err.txt"
check "pass-through run exits 0" "0" "$?"
contains "child stdout passes through" "pass-through-ok" "$workdir/out.txt"
contains "log file records the version" "version:" "$workdir/run.log"
contains "log file records the ok status" "status:.*ok" "$workdir/run.log"

# 16. child exit codes are ignored by design (runlim reports its own status)
runlim sh -c 'exit 42' > "$workdir/out.txt" 2> "$workdir/err.txt"
check "child exit code is ignored (runlim status ok = 0)" "0" "$?"

# 17-18. real-time limit
runlim -r 1 -o "$workdir/rt.log" sh -c 'while :; do :; done' > "$workdir/out.txt" 2>&1
check "real-time limit -r 1 exits 2 (out of time)" "2" "$?"
contains "real-time limit is reported in the log" "out of time" "$workdir/rt.log"

# 19-20. CPU-time limit — regression test for the RLIMIT_AS unit fix
runlim -t 1 -o "$workdir/cpu.log" sh -c 'i=0; while [ $i -lt 100000000 ]; do i=$((i+1)); done' > "$workdir/out.txt" 2>&1
check "cpu-time limit -t 1 exits 2 (out of time)" "2" "$?"
contains "cpu-time limit is reported in the log" "out of time" "$workdir/cpu.log"

# 21-22. long option forms
runlim --time-limit=1 sh -c 'i=0; while [ $i -lt 100000000 ]; do i=$((i+1)); done' > "$workdir/out.txt" 2>&1
check "--time-limit=1 exits 2 (out of time)" "2" "$?"
runlim --real-time-limit=1 sh -c 'while :; do :; done' > "$workdir/out.txt" 2>&1
check "--real-time-limit=1 exits 2 (out of time)" "2" "$?"

# 23-25. space limit through /proc sampling
runlim -s 1 -o "$workdir/sp.log" sh -c 'i=0; while [ $i -lt 100000000 ]; do i=$((i+1)); done' > "$workdir/out.txt" 2>&1
check "space limit -s 1 exits 3 (out of memory)" "3" "$?"
contains "space limit is reported in the log" "out of memory" "$workdir/sp.log"
runlim --space-limit=1 sh -c 'i=0; while [ $i -lt 100000000 ]; do i=$((i+1)); done' > "$workdir/out.txt" 2>&1
check "--space-limit=1 exits 3 (out of memory)" "3" "$?"

# 26-27. child signal status (SIGSEGV → 4)
runlim -o "$workdir/seg.log" sh -c 'kill -11 $$' > "$workdir/out.txt" 2>&1
check "child SIGSEGV exits 4" "4" "$?"
contains "child SIGSEGV is reported in the log" "segmentation fault" "$workdir/seg.log"

# 28. -k propagates the child signal to runlim itself (128 + 11)
runlim -k sh -c 'kill -11 $$' > "$workdir/out.txt" 2>&1
check "-k propagates the signal (exit 128+11)" "139" "$?"

# 29-31. default log target is stderr; child stdout stays on stdout
runlim sh -c 'echo child-stdout' > "$workdir/out.txt" 2> "$workdir/err.txt"
check "default run exits 0" "0" "$?"
contains "child stdout stays on stdout" "child-stdout" "$workdir/out.txt"
contains "default log goes to stderr" "runlim] version:" "$workdir/err.txt"

echo "# passed: $passed, failed: $failed"
if [ "$failed" -ne 0 ]; then
    exit 1
fi
exit 0
