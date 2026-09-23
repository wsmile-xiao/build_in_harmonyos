#!/bin/sh
# test_bluefish.sh — headless verification of the packaged bluefish binary.
#
# bluefish is a GTK3 GUI editor and HarmonyOS PC has no X server. These
# tests therefore cover every headless-verifiable surface of the installed
# binary:
#   1. upstream CLI contract: --version / --help (regression of behaviour
#      that is also reachable interactively);
#   2. the adaptation's --selftest option: 14 programmatic checks over
#      production code (rcfile config value codec, string helpers, word
#      count incl. UTF-8/empty inputs, integer parsing incl. error path,
#      libxml2 parsing success/failure, GLib/GTK runtime version);
#   3. the no-display failure path, proving the binary actually loads and
#      initialises the GTK3/GLib libraries it links.
set -eu

bluefish_bin="$1"
work_root=${TMPDIR:-$PWD}
log="$work_root/bluefish-test-$$.log"
trap 'rm -f "$log"' EXIT HUP INT TERM

asserts=0
failures=0

assert_true() {
    asserts=$((asserts + 1))
    if "$@" >/dev/null 2>&1; then
        printf 'bluefish-assert: %s: PASS\n' "$1"
    else
        printf 'bluefish-assert: %s: FAIL\n' "$1"
        failures=$((failures + 1))
    fi
}

assert_cond() {
    label=$1
    shift
    asserts=$((asserts + 1))
    if "$@" >/dev/null 2>&1; then
        printf 'bluefish-assert: %s: PASS\n' "$label"
    else
        printf 'bluefish-assert: %s: FAIL\n' "$label"
        failures=$((failures + 1))
    fi
}

assert_grep() {
    asserts=$((asserts + 1))
    if printf '%s' "$2" | grep -qF -- "$3"; then
        printf 'bluefish-assert: %s: PASS\n' "$1"
    else
        printf 'bluefish-assert: %s: FAIL\n' "$1"
        failures=$((failures + 1))
    fi
}

assert_eq() {
    asserts=$((asserts + 1))
    if [ "$2" = "$3" ]; then
        printf 'bluefish-assert: %s: PASS\n' "$1"
    else
        printf 'bluefish-assert: %s: FAIL (expected [%s], got [%s])\n' "$1" "$3" "$2"
        failures=$((failures + 1))
    fi
}

# --- package presence ---------------------------------------------------
assert_cond binary-exists test -f "$bluefish_bin"
assert_cond binary-executable test -x "$bluefish_bin"

# --- upstream CLI contract (headless) -----------------------------------
version_output=$("$bluefish_bin" --version 2>&1) || true
assert_eq version-rc0 "$("$bluefish_bin" --version >/dev/null 2>&1; echo $?)" 0
assert_grep version-line-1 "$version_output" "Bluefish Editor 2.2.16"
assert_grep version-line-2 "$version_output" "http://bluefish.openoffice.nl"

help_output=$("$bluefish_bin" --help 2>&1) || true
assert_eq help-rc0 "$("$bluefish_bin" --help >/dev/null 2>&1; echo $?)" 0
assert_grep help-usage "$help_output" "Usage:"
assert_grep help-version-option "$help_output" "--version"
assert_grep help-selftest-option "$help_output" "--selftest"

# --- adaptation self-test: 14 production checks -------------------------
set +e
selftest_output=$("$bluefish_bin" --selftest 2>&1)
selftest_rc=$?
set -e
assert_eq selftest-rc0 "$selftest_rc" 0
pass_count=$(printf '%s\n' "$selftest_output" | grep -o 'self-test: .*: PASS' | wc -l | tr -d ' ')
assert_eq selftest-14-checks "$pass_count" 14
assert_grep selftest-summary "$selftest_output" "self-test: PASS"
for check in \
    config-escape-roundtrip-colon \
    config-escape-roundtrip-nocolon \
    string-repeat \
    string-repeat-zero \
    string-truncate-found \
    string-truncate-missing \
    wordcount-empty \
    wordcount-ascii \
    wordcount-utf8 \
    int-parse-digits \
    int-parse-none \
    xml-parse-valid \
    glib-version \
    gtk-version
do
    assert_grep "check-$check" "$selftest_output" "self-test: $check: PASS"
done

# --- GUI cannot open a display on OHOS: must fail closed ---------------
# This exit path is reached only after GTK3/GLib were loaded and the GTK
# display initialisation ran, so it doubles as a library-linkage proof.
set +e
"$bluefish_bin" >"$log" 2>&1
no_display_rc=$?
set -e
# GLib g_error() aborts (rc 133/SIGTRAP on OHOS); any non-zero exit that
# carries the diagnostic counts as fail-closed.
asserts=$((asserts + 1))
if [ "$no_display_rc" -ne 0 ]; then
    printf 'bluefish-assert: no-display-nonzero: PASS\n'
else
    printf 'bluefish-assert: no-display-nonzero: FAIL (rc 0)\n'
    failures=$((failures + 1))
fi
assert_grep no-display-diagnostic "$(cat "$log")" "Cannot open display"

printf 'bluefish-test: %s assertions, %s failures\n' "$asserts" "$failures"
if [ "$failures" -ne 0 ]; then
    exit 1
fi
exit 0
