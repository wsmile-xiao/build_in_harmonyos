#!/data/service/hnp/bin/bash
# test_package/test.sh — functional smoke test for the dhex executable.
# Runs inside the conanrun env (PATH includes the installed bin/).
# -v/-h exit before ncurses UI startup, so no terminal is needed.
# -g paginates: gpl.c print_gpl() calls warte() every 24 lines, which does
# fgets(stdin) ("...Please press <Enter> to read on..."). With stdin as an
# open pipe (CI worker) that blocks forever -> 4h "without output" timeout
# (build #44099 hung at "[test 3/3] dhex -g"). Redirecting stdin from
# /dev/null gives immediate EOF, warte() returns at once, full GPL dumps
# non-interactively. All invocations use </dev/null defensively.
set -euo pipefail

# Test 1: exact version output (non-empty exact match, not a tautology)
echo "[test 1/3] dhex -v"
VER="$(dhex -v </dev/null 2>&1)"
echo "dhex -v output: ${VER}"
[ "${VER}" = "0.69" ] || {
    echo "FAIL: dhex -v printed [${VER}], expected [0.69]"
    exit 1
}
echo "PASS: version is exactly 0.69"

# Test 2: help screen mentions DHEX and is non-empty
echo "[test 2/3] dhex -h"
HELP="$(dhex -h </dev/null 2>&1)"
[ -n "${HELP}" ] || {
    echo "FAIL: dhex -h produced empty output"
    exit 1
}
echo "${HELP}" | grep -qi "DHEX" || {
    echo "FAIL: dhex -h output does not mention DHEX"
    exit 1
}
echo "PASS: help screen is non-empty and mentions DHEX"

# Test 3: license output contains the GPL text and is non-empty
# (stdin </dev/null is REQUIRED here — see header comment on warte()).
echo "[test 3/3] dhex -g"
GPL="$(dhex -g </dev/null 2>&1)"
[ -n "${GPL}" ] || {
    echo "FAIL: dhex -g produced empty output"
    exit 1
}
echo "${GPL}" | grep -qi "General Public License" || {
    echo "FAIL: dhex -g output does not contain the GPL text"
    exit 1
}
echo "PASS: license text is non-empty and contains the GPL"
