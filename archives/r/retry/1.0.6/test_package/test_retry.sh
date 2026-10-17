#!/bin/sh
# test_retry.sh — consumer-side regression tests for the packaged retry CLI.
#
# Upstream ships no test suite: there is no tests/ tree, Makefile.am defines
# only `bin_PROGRAMS = retry` (no TESTS/check_PROGRAMS/check-local) and the
# configure script has no test switch — `make check` executes zero cases.
# These assertions therefore exercise the installed binary's documented
# behaviour so a broken package cannot pass:
#   * criteria handling (success / fail / --until / --while) and --times
#   * stdin capture and replay across retries
#   * stdout routing: only the successful attempt's stdout reaches stdout,
#     the stdout of repeated attempts is routed to stderr
#   * exit-code propagation, error reporting and custom notification messages
#
# Every check emits exactly one TAP line; assertion_count in MANIFEST.yml is
# the number of TAP lines this script emits (28).

set -u

workdir="${TMPDIR:-/tmp}/retry-test-$$"
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

absent() {
    # absent <description> <needle> <file>
    desc=$1 needle=$2 file=$3
    if grep -q -- "$needle" "$file" 2>/dev/null; then
        failed=$((failed + 1))
        echo "not ok - $desc (unexpected: $needle)"
    else
        passed=$((passed + 1))
        echo "ok - $desc"
    fi
}

echo "1..28"

# Probe command: fails twice, succeeds on the third attempt, one line per try.
cat > "$workdir/probe.sh" <<'PROBE'
#!/bin/sh
n=$(cat "$COUNTER" 2>/dev/null || echo 0)
n=$((n + 1))
echo "$n" > "$COUNTER"
echo "attempt $n"
if [ "$n" -ge 3 ]; then
    exit 0
fi
exit 1
PROBE
chmod +x "$workdir/probe.sh"
COUNTER="$workdir/counter"
export COUNTER

# 1. the binary must be on PATH (installed into bin/ and exported by the package)
if command -v retry >/dev/null 2>&1; then
    check "retry binary is installed and on PATH" "0" "0"
else
    check "retry binary is installed and on PATH" "0" "1"
fi

# 2-3. version banner
version_out=$(retry -v </dev/null 2>&1)
check "retry -v exits 0" "0" "$?"
check "retry -v prints the 1.0.6 banner" "retry 1.0.6" "$version_out"

# 4-5. help text
retry --help </dev/null > "$workdir/help.txt" 2>&1
check "retry --help exits 0" "0" "$?"
contains "retry --help documents the repeat behaviour" "Repeat command until a criteria" "$workdir/help.txt"

# 6-8. a command that succeeds on the first try is not repeated
retry -d 0 -t 1 -- sh -c 'echo first-try-ok' </dev/null > "$workdir/out.txt" 2> "$workdir/err.txt"
check "first-try success exits 0" "0" "$?"
contains "first-try success passes stdout through" "first-try-ok" "$workdir/out.txt"
absent "first-try success does not back off" "trying again" "$workdir/err.txt"

# 9-13. repeat until success: 3 attempts, only the successful stdout on stdout
rm -f "$COUNTER"
retry -d 0 -t 5 --until=success -- sh "$workdir/probe.sh" </dev/null > "$workdir/out.txt" 2> "$workdir/err.txt"
check "retry --until=success exits 0 when the command eventually succeeds" "0" "$?"
check "retry --until=success stops after the third attempt" "3" "$(cat "$COUNTER" 2>/dev/null)"
contains "successful attempt stdout reaches stdout" "attempt 3" "$workdir/out.txt"
absent "repeated attempt stdout does not leak to stdout" "attempt 1" "$workdir/out.txt"
contains "retry reports the back-off on stderr" "trying again" "$workdir/err.txt"

# 14-15. --times exhausted: give up and propagate failure
retry -d 0 -t 2 -- false </dev/null > "$workdir/out.txt" 2> "$workdir/err.txt"
check "retry gives up after --times attempts with exit 1" "1" "$?"
contains "giving up is reported" "giving up." "$workdir/err.txt"

# 16. exit code of the last attempt is propagated
retry -d 0 -t 1 -- sh -c 'exit 42' </dev/null >/dev/null 2>&1
check "last attempt exit code is propagated (42)" "42" "$?"

# 17-19. stdin is captured and replayed to every attempt (including retries)
printf 'alpha\nbravo\n' > "$workdir/expected.txt"
cat > "$workdir/stdin_probe.sh" <<'PROBE'
#!/bin/sh
n=$(cat "$COUNTER" 2>/dev/null || echo 0)
n=$((n + 1))
echo "$n" > "$COUNTER"
cat > "$WORKDIR/attempt-$n.txt"
if [ "$n" -ge 2 ]; then
    exit 0
fi
exit 1
PROBE
chmod +x "$workdir/stdin_probe.sh"
WORKDIR="$workdir"
COUNTER="$workdir/stdin-counter"
export WORKDIR COUNTER
rm -f "$COUNTER"
printf 'alpha\nbravo\n' | retry -d 0 -t 3 -- sh "$workdir/stdin_probe.sh" > "$workdir/out.txt" 2> "$workdir/err.txt"
check "stdin retry run exits 0" "0" "$?"
check "first attempt received the captured stdin" "$(cat "$workdir/expected.txt")" "$(cat "$workdir/attempt-1.txt")"
check "stdin was replayed to the retried attempt" "$(cat "$workdir/expected.txt")" "$(cat "$workdir/attempt-2.txt")"

# 19-20. --until=fail stops at the first failing attempt
rm -f "$COUNTER"
retry -d 0 -t 5 --until=fail -- sh "$workdir/probe.sh" </dev/null > "$workdir/out.txt" 2> "$workdir/err.txt"
check "retry --until=fail exits with the failing status" "1" "$?"
check "retry --until=fail stops after the first attempt" "1" "$(cat "$COUNTER" 2>/dev/null)"

# 21. --while=fail does not repeat a command that never fails
retry -d 0 -t 3 --while=fail -- true </dev/null >/dev/null 2>&1
check "retry --while=fail exits 0 for an immediately successful command" "0" "$?"

# 23-24. invalid criteria are rejected with a diagnostic
retry --while=bogus -- true </dev/null > "$workdir/out.txt" 2> "$workdir/err.txt"
check "invalid --while value exits 1" "1" "$?"
contains "invalid --while value is reported" "While must contain" "$workdir/err.txt"

# 25-26. a command that cannot be executed is reported
retry -d 0 -t 1 -- /nonexistent/retry-probe-cmd </dev/null > "$workdir/out.txt" 2> "$workdir/err.txt"
check "non-executable command exits 1" "1" "$?"
contains "non-executable command is reported" "Could not execute" "$workdir/err.txt"

# 27-28. custom back-off message is used in the notification
rm -f "$COUNTER"
retry -d 0 -t 5 -m custom-msg -- sh "$workdir/probe.sh" </dev/null > "$workdir/out.txt" 2> "$workdir/err.txt"
check "custom --message run exits 0" "0" "$?"
contains "custom --message is shown in the back-off notification" "custom-msg returned" "$workdir/err.txt"

echo "# passed: $passed, failed: $failed"
if [ "$failed" -ne 0 ]; then
    exit 1
fi
exit 0
