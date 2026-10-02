#!/usr/bin/env bash
# test_package/test.sh — consumer-level functional test for the
# qmlrunner executable (Qt5 QML app runner), HarmonyOS PC aarch64.
#
# Runs in the conanrun env (PATH includes the installed bin/).
# QT_QPA_PLATFORM=offscreen + QT_QUICK_BACKEND=software are exported by
# the test_package conanfile (no display / GPU required).
#
# Cases:
#   positive 1: load a real QML window app (Timer -> Qt.quit()), rc=0
#   positive 2: same app with -noscale and an extra -path import path
#   negative 1: no arguments              -> usage, rc=255 (-1)
#   negative 2: unknown option            -> error, rc=253 (-3)
#   negative 3: duplicate application arg -> error, rc=254 (-2)
#   negative 4: missing QML file          -> error, rc=254 (-2)
#
# NOTE: `set -e` is intentionally NOT used — the negative controls must
# capture the expected non-zero exit codes of the CLI contract.
set -uo pipefail

fail() {
    echo "        [fail] $1"
    exit 1
}

check_rc() { # expected actual label
    if [ "$2" -ne "$1" ]; then
        fail "$3 (expected rc=$1, got rc=$2)"
    fi
}

# /tmp is read-only on OHOS; use $TMPDIR (set by the conan profile) or
# fall back to the current directory. Never touch the archive tree.
TEST_ROOT="$(mktemp -d "${TMPDIR:-$PWD}/qmlrunner-test.XXXXXX")" || fail "mktemp failed"
trap 'rm -rf "$TEST_ROOT"' EXIT INT TERM

mkdir -p "$TEST_ROOT/myapp/qml"
cp testapp/qml/myapp.qml "$TEST_ROOT/myapp/qml/myapp.qml" || fail "cannot stage myapp.qml"

echo "        [step] positive 1: qmlrunner -P <root> myapp"
out="$(qmlrunner -P "$TEST_ROOT" myapp 2>&1)"
rc=$?
check_rc 0 "$rc" "positive run"
echo "$out" | grep -q "Current locale:" || fail "missing 'Current locale:' line: $out"
echo "$out" | grep -q "Translation not found" || fail "missing translation fallback line: $out"
echo "        [ok] QML window loaded, event loop quit cleanly"

echo "        [step] positive 2: -noscale + extra -path (extra import path)"
out="$(qmlrunner -noscale -path "$TEST_ROOT/myapp/qml" -P "$TEST_ROOT" myapp 2>&1)"
rc=$?
check_rc 0 "$rc" "positive run with -noscale/-path"
echo "$out" | grep -q "Current locale:" || fail "missing 'Current locale:' line (run 2): $out"
echo "        [ok] -noscale / -path combination accepted"

echo "        [step] negative 1: no application name (usage)"
out="$(qmlrunner 2>&1)"
rc=$?
check_rc 255 "$rc" "no-args usage exit code"
echo "$out" | grep -q "Usage: qmlrunner" || fail "usage banner missing: $out"
echo "        [ok] usage + rc=255"

echo "        [step] negative 2: unknown option"
out="$(qmlrunner --bogus myapp 2>&1)"
rc=$?
check_rc 253 "$rc" "unknown option exit code"
echo "$out" | grep -q "Unknown option: --bogus" || fail "unknown option message missing: $out"
echo "        [ok] unknown option + rc=253"

echo "        [step] negative 3: duplicate application name"
out="$(qmlrunner app-one app-two 2>&1)"
rc=$?
check_rc 254 "$rc" "duplicate app name exit code"
echo "$out" | grep -q "Application name specified multiple times" || fail "duplicate app message missing: $out"
echo "        [ok] duplicate app name + rc=254"

echo "        [step] negative 4: QML application not found"
out="$(qmlrunner -P "$TEST_ROOT/absent" myapp 2>&1)"
rc=$?
check_rc 254 "$rc" "missing app exit code"
echo "$out" | grep -q "Cannot find" || fail "missing 'Cannot find' message: $out"
echo "        [ok] missing app + rc=254"

echo "        [ok] ALL PASS (2 positive + 4 negative cases)"
