#!/bin/sh
# test_clitest.sh — generic functional tests for the installed clitest tool.
#
# Every assertion runs the packaged script itself (`<interpreter> <pkg>/bin/clitest`),
# so this exercises the real tool, not a stub. The interpreter is passed
# explicitly because the packaged shebang points at /system/bin/sh, which only
# exists on HarmonyOS; the shebang itself is asserted in test_clitest_ohos.sh.
#
# Fixtures are written with printf, never with here-documents: HarmonyOS'
# /system/bin/sh backs each here-document with a temp file under /tmp, which is
# read-only there, and a failed here-document leaves the redirection target as
# an EMPTY file instead of aborting the script (CI build #56023).
#
# Usage: test_clitest.sh <path-to-clitest> [interpreter]
set -u

CLITEST="${1:?usage: test_clitest.sh <path-to-clitest> [interpreter]}"
SH="${2:-sh}"

pass=0
fail=0
ok() { echo "PASS: $1"; pass=$((pass + 1)); }
no() { echo "FAIL: $1 -- $2"; fail=$((fail + 1)); }

run() { "$SH" "$CLITEST" "$@" 2>&1; }

WORK="$(pwd)/clitest-tp-work"
rm -rf "$WORK"
mkdir -p "$WORK" || { echo "FAIL: cannot create work dir $WORK"; exit 1; }
# clitest needs a writable temp dir. Keep the environment's $TMPDIR when it is
# usable (the HarmonyOS CI worker provides one); fall back to a private dir in
# the writable build folder only when it is unset or not writable.
if [ -z "${TMPDIR:-}" ] || [ ! -d "$TMPDIR" ] || [ ! -w "$TMPDIR" ]; then
    TMPDIR="$WORK/tmp"
    mkdir -p "$TMPDIR"
    export TMPDIR
fi

# ── fixtures (printf only, see header) ──────────────────────────────────────
printf '%s\n' \
    "\$ echo ok" \
    "ok" \
    "\$ printf 'a\\nb\\n'" \
    "a" \
    "b" \
    "\$ echo inline                   #=> inline" \
    > "$WORK/pass.txt"

printf '%s\n' \
    "\$ echo good" \
    "good" \
    "\$ echo actual" \
    "expected" \
    > "$WORK/fail.txt"

printf '%s\n' \
    "\$ printf '1\\n2\\n3\\n'            #=> --lines 3" \
    "\$ echo hello                    #=> --text hello" \
    "\$ sh -c 'exit 3'                #=> --exit 3" \
    > "$WORK/inline.txt"

# Markdown-style: commands indented with a tab, parsed via --prefix tab
printf 'Doc heading\n\n\t$ echo md\n\tmd\n' > "$WORK/doc.md"

printf '%s\n' \
    "This file contains prose only, no command prompts at all." \
    > "$WORK/empty.txt"

printf '%s\n' \
    "\$ echo one" \
    "WRONG" \
    "\$ echo two" \
    "ALSO-WRONG" \
    > "$WORK/two-fails.txt"

printf '%s\n' \
    "\$ echo \"\$TP_MARKER\"" \
    "marker-value" \
    > "$WORK/preflight.txt"

# Refuse to continue on a silently empty fixture: report the real cause
# instead of a misleading "no test found" from clitest.
for f in "$WORK"/*.txt "$WORK"/*.md; do
    [ -s "$f" ] || { echo "FAIL: fixture $f is empty (shell could not write it)"; exit 1; }
done

# ── 1. --version ────────────────────────────────────────────────────────────
out=$(run --version)
if [ "$out" = "clitest 0.5.0" ]; then
    ok "--version prints 'clitest 0.5.0'"
else
    no "--version prints 'clitest 0.5.0'" "got '$out'"
fi

# ── 2. --help ───────────────────────────────────────────────────────────────
out=$(run --help)
rc=$?
if [ $rc -eq 0 ] && echo "$out" | grep -qi '^usage: clitest'; then
    ok "--help exits 0 and shows usage"
else
    no "--help exits 0 and shows usage" "rc=$rc out='$(echo "$out" | head -n 1)'"
fi

# ── 3. all-passing test file ────────────────────────────────────────────────
out=$(run --progress none "$WORK/pass.txt")
rc=$?
if [ $rc -eq 0 ] && echo "$out" | grep -q '^OK: 3 of 3 tests passed$'; then
    ok "3-test file passes and exits 0"
else
    no "3-test file passes and exits 0" "rc=$rc out='$(echo "$out" | tail -n 1)'"
fi

# ── 4. failing test file is reported and exits non-zero ─────────────────────
out=$(run --progress none "$WORK/fail.txt")
rc=$?
if [ $rc -ne 0 ] && echo "$out" | grep -q 'FAIL: 1 of 2 tests failed'; then
    ok "failing file reports 1 of 2 failed and exits non-zero"
else
    no "failing file reports 1 of 2 failed and exits non-zero" "rc=$rc out='$(echo "$out" | tail -n 1)'"
fi

# ── 5. the diff of a failure names the expected and the actual text ─────────
out=$(run --progress none "$WORK/fail.txt")
if echo "$out" | grep -q -- '-expected' && echo "$out" | grep -q -- '+actual'; then
    ok "failure output contains the expected/actual diff"
else
    no "failure output contains the expected/actual diff" "$(echo "$out" | tr '\n' '|')"
fi

# ── 6. inline matching methods (--lines / --text / --exit) ──────────────────
out=$(run --progress none "$WORK/inline.txt")
rc=$?
if [ $rc -eq 0 ] && echo "$out" | grep -q '^OK: 3 of 3 tests passed$'; then
    ok "inline matchers --lines/--text/--exit all pass"
else
    no "inline matchers --lines/--text/--exit all pass" "rc=$rc out='$(echo "$out" | tail -n 1)'"
fi

# ── 7. --list enumerates the test commands ──────────────────────────────────
out=$(run --list "$WORK/pass.txt")
if echo "$out" | grep -q 'echo ok' && echo "$out" | grep -q 'echo inline'; then
    ok "--list enumerates the test commands"
else
    no "--list enumerates the test commands" "$(echo "$out" | tr '\n' '|')"
fi

# ── 8. --prefix tab parses a Markdown-style document ────────────────────────
out=$(run --progress none --prefix tab "$WORK/doc.md")
rc=$?
if [ $rc -eq 0 ] && echo "$out" | grep -q '^OK: 1 of 1 test passed$'; then
    ok "--prefix tab parses an indented Markdown document"
else
    no "--prefix tab parses an indented Markdown document" "rc=$rc out='$(echo "$out" | tail -n 1)'"
fi

# ── 9. --first stops at the first failure ───────────────────────────────────
out=$(run --progress none --first "$WORK/two-fails.txt")
rc=$?
if [ $rc -ne 0 ] && echo "$out" | grep -q '\[FAILED #1' && ! echo "$out" | grep -q '\[FAILED #2'; then
    ok "--first aborts after the first failing test"
else
    no "--first aborts after the first failing test" "rc=$rc out='$(echo "$out" | tr '\n' '|')'"
fi

# ── 10. a file with no tests is rejected ────────────────────────────────────
out=$(run --progress none "$WORK/empty.txt")
rc=$?
if [ $rc -ne 0 ] && echo "$out" | grep -qi 'no test found'; then
    ok "file without tests is rejected with 'no test found'"
else
    no "file without tests is rejected with 'no test found'" "rc=$rc out='$(echo "$out" | tail -n 1)'"
fi

# ── 11. --pre-flight runs a setup command before the tests ──────────────────
out=$(run --progress none --pre-flight 'TP_MARKER=marker-value' "$WORK/preflight.txt")
rc=$?
if [ $rc -eq 0 ] && echo "$out" | grep -q '^OK: 1 of 1 test passed$'; then
    ok "--pre-flight command is executed before the tests"
else
    no "--pre-flight command is executed before the tests" "rc=$rc out='$(echo "$out" | tail -n 1)'"
fi

# ── 12. a non-existent test file is an error ────────────────────────────────
out=$(run "$WORK/does-not-exist.txt")
rc=$?
if [ $rc -ne 0 ] && echo "$out" | grep -qi 'cannot read'; then
    ok "missing test file is reported as an error"
else
    no "missing test file is reported as an error" "rc=$rc out='$(echo "$out" | tail -n 1)'"
fi

rm -rf "$WORK"

echo "----------------------------------------"
echo "generic: $pass passed, $fail failed"
test "$fail" -eq 0
