#!/usr/bin/env bash
# Consumer test for multirun 1.1.3 — real execution of the installed binary,
# mirroring the 4 upstream tests.bats cases.
set -e
cd "$(dirname "$0")"

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

# Test 1: simple command invocation writes a result file
rm -f resultfile
multirun "sh -c 'echo test > resultfile'"
[ -e resultfile ] || fail "resultfile not created"
[ "$(cat resultfile)" = "test" ] || fail "unexpected content: $(cat resultfile)"
rm -f resultfile

# Test 2: multiple commands run concurrently
rm -f resultfile1 resultfile2
multirun \
    "sh -c 'echo test > resultfile1; sleep 1'" \
    "sh -c 'echo test > resultfile2; sleep 1'"
[ -e resultfile1 ] || fail "resultfile1 not created"
[ -e resultfile2 ] || fail "resultfile2 not created"
[ "$(cat resultfile1)" = "test" ] || fail "unexpected content1: $(cat resultfile1)"
[ "$(cat resultfile2)" = "test" ] || fail "unexpected content2: $(cat resultfile2)"
rm -f resultfile1 resultfile2

# Test 3: all children exit 0 -> multirun returns 0
multirun "sh -c 'exit 0'"

# Test 4: a failing child -> multirun returns 255 (-1)
if multirun "sh -c 'exit 1'"; then
    fail "expected nonzero exit when a child fails"
fi

echo "test multirun 1.1.3: OK"