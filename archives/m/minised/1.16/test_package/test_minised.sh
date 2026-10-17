#!/bin/sh
# test_minised.sh — L1 functional test for the packaged minised binary.
# Called by test_package/conanfile.py test() with the package's minised path.
#
# Runs real sed transformations (not --help/--version) and asserts the output:
#   1. Substitution  : echo 'hello world' | s/world/OpenHarmony/  -> hello OpenHarmony
#   2. Line deletion : delete a line matching a pattern            -> remaining line only
#   3. Simple regex  : Kleene-star / grouped substitution           -> transformed text
set -eu

MINISED="$1"

# Sanity: the binary exists and is runnable.
"$MINISED" --version >/dev/null 2>&1 || true

# ── Test 1: substitution (required example) ──
out=$(printf 'hello world\n' | "$MINISED" 's/world/OpenHarmony/')
expected='hello OpenHarmony'
if [ "$out" != "$expected" ]; then
    echo "FAIL: substitution test"
    echo "  expected: $expected"
    echo "  got:      $out"
    exit 1
fi

# ── Test 2: line deletion ──
out=$(printf 'keep me\ndelete me\nkeep too\n' | "$MINISED" '/delete me/d')
expected_keep1='keep me'
expected_keep2='keep too'
got1=$(printf '%s\n' "$out" | sed -n '1p')
got2=$(printf '%s\n' "$out" | sed -n '2p')
if [ "$got1" != "$expected_keep1" ] || [ "$got2" != "$expected_keep2" ]; then
    echo "FAIL: line deletion test"
    echo "  expected: $expected_keep1 / $expected_keep2"
    echo "  got:      $got1 / $got2"
    exit 1
fi
# A second deletion assertion: delete ALL lines matching a word.
out=$(printf 'a\nb\na\n' | "$MINISED" '/^a$/d')
if [ "$out" != "b" ]; then
    echo "FAIL: delete-all test"
    echo "  expected: b"
    echo "  got:      $out"
    exit 1
fi

# ── Test 3: simple regex (Kleene star over a single char) ──
# s/a*/x/g matches runs of 'a' (including the empty match at end-of-line),
# so 'aaab' -> 'xbx'. This mirrors the upstream tests/s-star case
# ('aaan' -> 'xnx' under the same script).
out=$(printf 'aaab\n' | "$MINISED" 's/a*/x/g')
if [ "$out" != "xbx" ]; then
    echo "FAIL: regex star test"
    echo "  expected: xbx"
    echo "  got:      $out"
    exit 1
fi

# ── Test 4: backreference replacement (&) ──
# & in the RHS expands to the matched text.
out=$(printf 'cat\n' | "$MINISED" 's/c/[&]/')
if [ "$out" != "[c]at" ]; then
    echo "FAIL: backreference test"
    echo "  expected: [c]at"
    echo "  got:      $out"
    exit 1
fi

echo "PASS: minised functional tests (substitution, deletion, regex, backref)"
exit 0
