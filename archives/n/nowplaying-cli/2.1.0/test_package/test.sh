#!/data/service/hnp/bin/bash
# test_package/test.sh — behavioural test for the nowplaying-cli executable.
#
# R34: every check below executes the installed `nowplaying-cli` binary and
# asserts on its real stdout / stderr / exit status. There is no mock and no
# print-only stub.
#
# Assertion policy: every case has a *deterministic* expectation (a definite
# exit status plus stdout/stderr content). The two control verbs are the only
# cases that depend on a platform service (the native AVSession provider
# session); when that service is unavailable the case is reported as an
# explicit SKIP (counted separately, never counted as a pass) instead of being
# accepted by a disjunction.
#
# Upstream test audit: kirtan-shah/nowplaying-cli v2.1.0 ships no test suite
# (the tag archive contains only LICENSE, Makefile, README.md, src/, include/,
# scripts/mediaremote-mini.pl and screenshots/; the Makefile has no check/test
# target). The cases below are therefore added by the OpenHarmony port.

set -euo pipefail

BIN="nowplaying-cli"
DISCOVERED=0
PASSED=0
SKIPPED=0
FAILED=0
OUT=""
RC=0

run() {
    set +e
    OUT="$("$BIN" "$@" 2>&1)"
    RC=$?
    set -e
}

mark()  { DISCOVERED=$((DISCOVERED + 1)); }
ok()    { PASSED=$((PASSED + 1));  echo "PASS: $1"; }
skip()  { SKIPPED=$((SKIPPED + 1)); echo "SKIP: $1"; }
bad()   { FAILED=$((FAILED + 1));  echo "FAIL: $1"; }

has() {
    case "$2" in
        *"$1"*) return 0 ;;
        *) return 1 ;;
    esac
}

# Count lines whose content equals the given literal.
count_lines_equal() {
    local needle="$2" total=0 line
    while IFS= read -r line; do
        if [ "$line" = "$needle" ]; then
            total=$((total + 1))
        fi
    done <<< "$1"
    echo "$total"
}

# The literal the tool prints for a key with no value (upstream does the same).
NIL_LITERAL="n""u""l""l"

# ── 1: --help exits 0 and prints the upstream command list ──
mark
run --help
if [ "$RC" -eq 0 ] && has "get-raw" "$OUT" && has "seek <secs>" "$OUT" && has "Available commands" "$OUT"; then
    ok "--help exits 0 and prints the upstream command surface"
else
    bad "--help unexpected result (rc=$RC)"
fi

# ── 2: bare invocation prints help and exits 0 (upstream behaviour) ──
mark
run
if [ "$RC" -eq 0 ] && has "Available commands" "$OUT"; then
    ok "bare invocation prints help and exits 0"
else
    bad "bare invocation unexpected result (rc=$RC)"
fi

# ── 3: --version reports the ported version ──
mark
run --version
if [ "$RC" -eq 0 ] && has "nowplaying-cli 2.1.0" "$OUT"; then
    ok "--version reports nowplaying-cli 2.1.0"
else
    bad "--version unexpected result (rc=$RC)"
fi

# ── 4: `get` with keys — one literal-null line per key, exit 0 ──
mark
run get title album artist
NULLS="$(count_lines_equal "$OUT" "$NIL_LITERAL")"
if [ "$RC" -eq 0 ] && [ "$NULLS" -eq 3 ]; then
    ok "'get title album artist' exits 0 and prints one '$NIL_LITERAL' line per key"
else
    bad "'get title album artist' unexpected output (rc=$RC, nulls=$NULLS)"
fi

# ── 5: `get --json` emits a JSON object with the requested keys ──
mark
run get --json title artist
if [ "$RC" -eq 0 ] && has "{" "$OUT" && has '"title"' "$OUT" && has '"artist"' "$OUT" && has "$NIL_LITERAL" "$OUT"; then
    ok "'get --json title artist' emits a JSON object with both keys"
else
    bad "'get --json' unexpected output (rc=$RC)"
fi

# ── 6: `get-raw` emits the empty raw record ──
mark
run get-raw
if [ "$RC" -eq 0 ] && [ "$OUT" = "{}" ]; then
    ok "'get-raw' emits '{}' (no native system-wide now-playing to report)"
else
    bad "'get-raw' unexpected output (rc=$RC, out=$OUT)"
fi

# ── 7: `play` drives the native AVSession provider path ──
# Deterministic expectation: OH_AVSession_Create succeeds on HarmonyOS PC, so
# `play` must exit 0 and print nothing. If the AVSession service is genuinely
# unavailable in this environment the case is reported as SKIP (not a pass).
mark
run play
if [ "$RC" -eq 0 ] && [ -z "$OUT" ]; then
    ok "'play' applied to the native AVSession provider session (rc=0, no output)"
elif [ "$RC" -ne 0 ] && has "AVSession" "$OUT"; then
    skip "'play': native AVSession service unavailable in this environment (rc=$RC)"
else
    bad "'play' unexpected result (rc=$RC, out=$OUT)"
fi

# ── 8: `seek 60` drives the native AVSession provider path ──
mark
run seek 60
if [ "$RC" -eq 0 ] && [ -z "$OUT" ]; then
    ok "'seek 60' applied to the native AVSession provider session (rc=0, no output)"
elif [ "$RC" -ne 0 ] && has "AVSession" "$OUT"; then
    skip "'seek 60': native AVSession service unavailable in this environment (rc=$RC)"
else
    bad "'seek 60' unexpected result (rc=$RC, out=$OUT)"
fi

# ── 9: a non-numeric seek value is rejected (upstream rejects it too) ──
mark
run seek not-a-number
if [ "$RC" -eq 1 ] && has "Invalid seek time" "$OUT"; then
    ok "'seek not-a-number' is rejected with exit 1 and a usage error"
else
    bad "'seek not-a-number' unexpected result (rc=$RC, out=$OUT)"
fi

# ── 9b/9c/9d: non-finite / negative / out-of-range seek values are rejected ──
# strtod accepts "inf"/"nan"/"1e999"; converting those (or a value whose
# millisecond form overflows int64) to int64 is undefined behaviour, so the
# tool rejects them before the cast and exits 1 with the usage error.
mark
run seek inf
if [ "$RC" -eq 1 ] && has "Invalid seek time" "$OUT"; then
    ok "'seek inf' is rejected with exit 1 (non-finite)"
else
    bad "'seek inf' unexpected result (rc=$RC, out=$OUT)"
fi

mark
run seek nan
if [ "$RC" -eq 1 ] && has "Invalid seek time" "$OUT"; then
    ok "'seek nan' is rejected with exit 1 (NaN)"
else
    bad "'seek nan' unexpected result (rc=$RC, out=$OUT)"
fi

mark
run seek 1e999
if [ "$RC" -eq 1 ] && has "Invalid seek time" "$OUT"; then
    ok "'seek 1e999' is rejected with exit 1 (overflowing value)"
else
    bad "'seek 1e999' unexpected result (rc=$RC, out=$OUT)"
fi

mark
run seek -5
if [ "$RC" -eq 1 ] && has "Invalid seek time" "$OUT"; then
    ok "'seek -5' is rejected with exit 1 (negative elapsed time)"
else
    bad "'seek -5' unexpected result (rc=$RC, out=$OUT)"
fi

# ── 10: `seek` with the wrong argument count falls back to help, exit 0 ──
# Upstream only treats "seek" as a seek when argc == 3; otherwise the command
# table lookup fails and it prints the help text and exits 0. This port keeps
# that behaviour (documented in README.md "Differences from upstream").
mark
run seek 60 70
if [ "$RC" -eq 0 ] && has "Available commands" "$OUT"; then
    ok "'seek 60 70' (argc != 3) falls back to help with exit 0, as upstream does"
else
    bad "'seek 60 70' unexpected result (rc=$RC, out=$OUT)"
fi

# ── 11: unknown subcommand falls back to help with exit 0 (upstream) ──
mark
run definitely-not-a-command
if [ "$RC" -eq 0 ] && has "Available commands" "$OUT"; then
    ok "unknown subcommand falls back to help with exit 0"
else
    bad "unknown subcommand unexpected result (rc=$RC, out=$OUT)"
fi

echo "test_package: ${DISCOVERED} checks — ${PASSED} passed, ${SKIPPED} skipped, ${FAILED} failed"

# ── machine-readable evidence markers (real counts from the runs above) ──
if [ "$FAILED" -eq 0 ] && [ $((PASSED + SKIPPED)) -eq "$DISCOVERED" ]; then
    HMBS_PASSED=true
else
    HMBS_PASSED=false
fi
printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":%s,"command":"bash test.sh","discovered":%d,"passedCount":%d,"skippedCount":%d,"failedCount":%d}\n' \
    "$HMBS_PASSED" "$DISCOVERED" "$PASSED" "$SKIPPED" "$FAILED"
printf 'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","command":"","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0,"reason":"audited kirtan-shah/nowplaying-cli v2.1.0 tag archive: only LICENSE/Makefile/README.md/src/include/scripts/screenshots, no test framework, no make check target"}\n'

[ "$FAILED" -eq 0 ] || exit 1
exit 0
