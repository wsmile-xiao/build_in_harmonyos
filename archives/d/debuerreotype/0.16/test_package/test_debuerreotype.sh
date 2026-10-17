#!/usr/bin/env bash
# test_package/test_debuerreotype.sh — functional smoke test for debuerreotype scripts.
# Runs inside the conanrun env (PATH includes the installed bin/).
# Portable shebang: /data/service/hnp/bin/bash is absent on some workers.
set -eu
# _BASH = current interpreter when invoked as "$bash script.sh", else PATH lookup.
_BASH="${BASH:-$(command -v bash 2>/dev/null || echo bash)}"
# Never run Bash sources under POSIX sh: it misparses arrays as
# "syntax error: unexpected '('". Require a real bash interpreter.
if ! command -v "$_BASH" >/dev/null 2>&1; then
    echo "FAIL: bash interpreter not found on worker (tried BASH env and PATH); cannot run debuerreotype Bash entry points"
    exit 1
fi

# Test 1: expected entry scripts are on PATH
echo "[test] entry scripts present"
for prog in debuerreotype-version debuerreotype-tar debuerreotype-init debuerreotype-chroot debuerreotype-minimizing-config; do
    command -v "$prog" >/dev/null 2>&1 || {
        echo "FAIL: $prog not found on PATH"
        exit 1
    }
done
echo "OK entry scripts present"

# Test 2: bash -n syntax check over installed entries
echo "[test] bash -n syntax"
for prog in debuerreotype-version debuerreotype-tar debuerreotype-init debuerreotype-chroot debuerreotype-minimizing-config debuerreotype-apt-get debuerreotype-debian-sources-list debuerreotype-fixup debuerreotype-recalculate-epoch debuerreotype-slimify; do
    f="$(command -v "$prog")"
    "$_BASH" -n "$f" || {
        echo "FAIL: bash -n $prog"
        exit 1
    }
done
echo "OK syntax"

# Test 3: version smoke — really executes the script (sources
# .constants.sh, parses options via getopt, reads VERSION)
echo "[test] debuerreotype-version"
debuerreotype-version 2>&1 | grep -q "0.16" || {
    echo "FAIL: debuerreotype-version did not report 0.16"
    exit 1
}
echo "OK version reports 0.16"

# Test 4: help smoke — option parsing path (--help prints usage + version)
# NOTE: debuerreotype-version sources .constants.sh with empty usage strings
# (source ... '' ''), so its usageStr is just "\n" and --help prints only
# "debuerreotype version <v>" with NO literal "usage:" line (upstream design,
# verified against tag 0.16 scripts/debuerreotype-version + .constants.sh).
# Assert the real output; a script with real usage lines
# (debuerreotype-tar) covers the "usage:" wording in the same test.
echo "[test] debuerreotype-version --help"
debuerreotype-version --help 2>&1 | grep -qi "debuerreotype version" || {
    echo "FAIL: debuerreotype-version --help did not print version line"
    exit 1
}
debuerreotype-version --help 2>&1 | grep -q "0.16" || {
    echo "FAIL: debuerreotype-version --help did not report 0.16"
    exit 1
}
debuerreotype-tar --help 2>&1 | grep -qi "usage" || {
    echo "FAIL: debuerreotype-tar --help did not print usage"
    exit 1
}
echo "OK help"

# Test 5: helper payload installed alongside entries (sourced at runtime)
echo "[test] helper files present"
bindir="$(dirname "$(command -v debuerreotype-version)")"
test -f "$bindir/.constants.sh" || {
    echo "FAIL: $bindir/.constants.sh missing"
    exit 1
}
test -f "$bindir/../VERSION" || {
    echo "FAIL: VERSION missing next to bin/"
    exit 1
}
echo "OK helpers present"
