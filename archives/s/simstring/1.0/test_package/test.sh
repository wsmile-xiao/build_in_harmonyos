#!/data/service/hnp/bin/bash
# test_package CLI smoke for simstring 1.0 (OHOS/HarmonyOS PC).
# Usage: test.sh <package-bin-dir>
#
# The bin dir is passed explicitly because the package is header-library:
# conan's VirtualRunEnv only contributes cpp_info.bindirs to PATH when the
# require has run=True (tools/env/virtualrunenv.py:79 `if require.run:`),
# so conanrun PATH never contains package/bin and a bare `simstring` would
# fail with 127 (abiword-plugin-* test_package precedent for arg passing).
#
# Five checks against the packaged binary: version banner, database build
# from stdin, exact + cosine query output, help text. All artifacts are
# written to the current working directory (device /tmp is read-only; see
# notes/device-facts.md §一.1).
set -u

BIN_DIR="${1:?usage: test.sh <package-bin-dir>}"
SIM="$BIN_DIR/simstring"

fail=0
note() { printf '[TP] %s\n' "$*"; }

if [ ! -x "$SIM" ]; then
    note "FAIL packaged binary missing/not executable: $SIM"
    exit 1
fi

# [1] version banner
v_out="$("$SIM" -v 2>&1)"; v_rc=$?
if [ "$v_rc" -eq 0 ] && printf '%s\n' "$v_out" | grep -q "SimString 1.0"; then
    note "PASS version banner (SimString 1.0)"
else
    note "FAIL version banner (rc=$v_rc)"; fail=1
fi

# [2] build a 3-entry database from stdin
rm -f tp.db tp.db.* >/dev/null 2>&1
b_out="$(printf 'apple\napplication\nbanana\n' | "$SIM" -b -d tp.db 2>&1)"; b_rc=$?
if [ "$b_rc" -eq 0 ] && printf '%s\n' "$b_out" | grep -q "Number of strings: 3"; then
    note "PASS build phase reports 3 strings"
else
    note "FAIL build phase (rc=$b_rc)"; fail=1
fi

# [3] exact retrieval: query word must come back verbatim
e_out="$(printf 'apple\n' | "$SIM" -d tp.db -s exact -t 1.0 -q 2>&1)"; e_rc=$?
if [ "$e_rc" -eq 0 ] && printf '%s\n' "$e_out" | grep -q "apple"; then
    note "PASS exact query retrieves 'apple'"
else
    note "FAIL exact query (rc=$e_rc)"; fail=1
fi

# [4] cosine retrieval at threshold 0.5 also resolves 'apple'
c_out="$(printf 'apple\n' | "$SIM" -d tp.db -s cosine -t 0.5 -q 2>&1)"; c_rc=$?
if [ "$c_rc" -eq 0 ] && printf '%s\n' "$c_out" | grep -q "apple"; then
    note "PASS cosine query retrieves 'apple'"
else
    note "FAIL cosine query (rc=$c_rc)"; fail=1
fi

# [5] help text documents the similarity options (option parsing sanity)
h_out="$("$SIM" -h 2>&1)"; h_rc=$?
if [ "$h_rc" -eq 0 ] && printf '%s\n' "$h_out" | grep -q -- "--similarity"; then
    note "PASS help lists --similarity"
else
    note "FAIL help output (rc=$h_rc)"; fail=1
fi

if [ "$fail" -eq 0 ]; then
    note "ALL CLI CHECKS PASSED (5/5)"
else
    note "CLI CHECKS FAILED"
fi
exit "$fail"
