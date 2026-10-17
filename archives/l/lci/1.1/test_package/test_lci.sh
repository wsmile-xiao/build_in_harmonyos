#!/usr/bin/env bash
# Test package for lci 1.1.
#
# This exercises the interpreter's real core functionality, mirroring the
# upstream CTest suite plus prelude arithmetic:
#   T1 queens       (upstream test)      : pure-lambda N-queens solver, all 10
#                                         solutions of the 5-queens instance
#   T2 fixed_point  (upstream test)      : Y-combinator fixed-point driver and
#                                         list Append on the output list
#   T3 arithmetic   (prelude functions)  : Mult / Exp / Monus / Length
#
# Output format notes (verified against the real interpreter):
#   - results print on their own line, preceded by a blank line;
#   - church numeral 1 prints as alias "I" (e.g. "[I, 3, 5, 2, 4]");
#   - queens prints the 10 solutions as one list-of-lists line;
#   - fixed_point prints "13 cycles removed using fixed point combinator Y."
#     followed by the append result.
#
# Usage: test_lci.sh <path-to-lci> [workdir]
# The script runs in [workdir] (default: its own directory) because
# Consult 'queens.lci' resolves the file relative to the current working
# directory; the packaged .lcirc prelude is found through the DATADIR
# compiled into the lci binary (package share/lci directory).
# Bash script (the test_package conanfile runs it through bash): needs
# local, pipefail-aware pipelines, and errexit. The lci invocation and the
# sed|head diagnostic pipeline are || true-guarded so a failing interpreter
# run still reports FAIL through the grep assertion below instead of
# aborting the script and losing the remaining checks' diagnostics.
set -euo pipefail

LCI="${1:?usage: test_lci.sh <path-to-lci> [workdir]}"
WORKDIR="${2:-$(cd "$(dirname "$0")" && pwd)}"
ret=0

check() {
    local name="$1"; shift
    local expected="$1"; shift
    local input="$1"; shift
    local out
    out="$(cd "$WORKDIR" && printf '%s\nQuit\n' "$input" | "$LCI" 2>&1)" || true
    if printf '%s\n' "$out" | grep -qE "$expected"; then
        echo "PASS: $name"
    else
        echo "FAIL: $name"
        echo "--- input: $input"
        printf '%s\n' "$out" | sed 's/^/    /' | head -20 || true
        ret=1
    fi
}

# T1: upstream queens — all 10 solutions of Queens 5 (church numeral 1
# prints as alias I). Expected full solution list, anchored as a single
# line. This is the same expression the upstream CTest queens test runs.
check "queens (upstream CTest)" \
    "^\[\[I, 3, 5, 2, 4\], \[I, 4, 2, 5, 3\], \[2, 4, I, 3, 5\], \[2, 5, 3, I, 4\], \[3, I, 4, 2, 5\], \[3, 5, 2, 4, I\], \[4, I, 3, 5, 2\], \[4, 2, 5, 3, I\], \[5, 2, 4, I, 3\], \[5, 3, I, 4, 2\]\]$" \
    "Consult 'queens.lci'; Queens 5"

# T2: upstream fixed_point — Y-combinator removes 13 cycles, then
# Append [3,4,[]] [5] yields [3, 4, [], 5]. Same expression as the
# upstream CTest fixed_point test (PASS_REGULAR_EXPRESSION equivalent).
check "fixed_point cycles (upstream CTest)" \
    "cycles removed using fixed point combinator Y" \
    "FixedPoint; Append [3,4,[]] [5]"
check "fixed_point result (upstream CTest)" \
    "^\[3, 4, \[\], 5\]$" \
    "FixedPoint; Append [3,4,[]] [5]"

# T3: prelude arithmetic on church numerals, printing decimal results.
check "arithmetic Mult 3 4" "^12$" "Mult 3 4"
check "arithmetic Exp 2 10" "^1024$" "Exp 2 10"
check "arithmetic Monus 20 8" "^12$" "Monus 20 8"
check "arithmetic Length [1,2,3,4,5]" "^5$" "Length [1,2,3,4,5]"

exit "$ret"
