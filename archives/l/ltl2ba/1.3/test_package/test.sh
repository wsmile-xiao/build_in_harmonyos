#!/bin/bash
# test.sh — ltl2ba 1.3 test (R34)
#
# Verifies the ltl2ba binary installed by the Conan package (NOT the
# source-tree binary — R7) translates LTL formulae into Büchi automata
# never claims.
#
# Section A — Upstream official test (from README §3 EXECUTING):
#   The upstream README documents usage as `./ltl2ba -f 'formula'` with
#   the temporal operators [] <> U V X. ltl2ba ships NO test suite, NO
#   make test/check target, and NO test data (verified by inspecting the
#   1.3 source tree). The README's only test method is running the tool
#   on a formula. We mirror that with the documented `U` operator on
#   `a U b`, exactly the README invocation form `./ltl2ba -f 'a U b'`.
#
# Section B — Additional test_package tests:
#   []p, <>p, p U q — three canonical LTL formulae checking the other
#   documented temporal operators and verifying Büchi automata content.
#
# The ltl2ba binary path is passed as $1.

set -euo pipefail

LTL2BA="${1:?usage: test.sh <path-to-ltl2ba>}"

echo "=== ltl2ba 1.3 test ==="
echo "binary: $LTL2BA"

pass=0
fail=0

check_formula() {
    local label="$1"
    local formula="$2"
    local expect_accept="$3"
    echo "--- test: $label  (formula: $formula) ---"
    if out=$("$LTL2BA" -f "$formula" 2>&1); then
        rc=0
    else
        rc=$?
    fi
    if [ "$rc" -ne 0 ]; then
        echo "        [fail] $label: ltl2ba exited with code $rc"
        echo "$out"
        fail=$((fail + 1))
        return
    fi
    echo "        [ok]   $label: exit code 0"
    # A valid never claim opens with "never { /* formula */"
    if echo "$out" | grep -q "^never {"; then
        echo "        [ok]   $label: 'never {' header present (Büchi automaton)"
    else
        echo "        [fail] $label: no 'never {' header in output"
        echo "$out"
        fail=$((fail + 1))
        return
    fi
    # A never claim always contains an acceptance state (accept_init or
    # accept_all), which is the Büchi acceptance condition.
    if echo "$out" | grep -qE "$expect_accept"; then
        echo "        [ok]   $label: acceptance state ('$expect_accept') present"
    else
        echo "        [fail] $label: no acceptance state ('$expect_accept') found"
        echo "$out"
        fail=$((fail + 1))
        return
    fi
    pass=$((pass + 1))
}

# ============================================================
# Section A — Upstream official test (README §3 EXECUTING form)
# ============================================================
# README documents: ./ltl2ba -f 'formula'  with operators [] <> U V X.
# `a U b` uses the documented `U` (until) operator — the canonical
# README invocation form. Upstream has no other test suite.
check_formula "upstream-official-aUb" "a U b" "accept_(init|all):"

# ============================================================
# Section B — Additional test_package tests (canonical formulae)
# ============================================================

# []p (always p) — a self-loop accept state guarded by (p)
check_formula "additional-always-[]p" "[]p" "accept_init:"

# <>p (eventually p) — init + accept_all sink guarded by (p)
check_formula "additional-eventually-<>p" "<>p" "accept_all:"

# p U q (p until q) — init with (p)/(q) branches + accept_all
check_formula "additional-until-pUq" "p U q" "accept_all:"

echo "=== results: $pass passed, $fail failed ==="
if [ "$fail" -ne 0 ]; then
    exit 1
fi
echo "=== All tests passed ==="
