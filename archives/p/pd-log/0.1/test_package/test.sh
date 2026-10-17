#!/usr/bin/env bash
# test.sh — functional test for the packaged pd-log Pure Data externals.
#
# Two layers:
#   1. package layout: every object, help patch, meta file and licence the
#      recipe promises is actually installed under lib/pd-externals/log;
#   2. native load: pdlog_dlopen_test (built by test_package/build()) runs on
#      the target and dlopen()s each external, resolving its Pd entry point.
#
# Environment (set by test_package/conanfile.py):
#   CONAN_PD_LOG_FOLDER  package folder of the pd-log dependency
#   PDLOG_EXPECT_MACHINE ELF e_machine the externals must carry
#                        (183 = EM_AARCH64, 62 = EM_X86_64, empty = skip)

# No `set -e` on purpose: every check below must run so that one run reports
# all failures, and the exit status is decided by the explicit FAIL count at
# the end. `nounset` + `pipefail` still catch unset variables and broken pipes.
set -uo pipefail

PKG="${CONAN_PD_LOG_FOLDER:?CONAN_PD_LOG_FOLDER not set}"
EXT_DIR="$PKG/lib/pd-externals/log"
NATIVE_TEST="./pdlog_dlopen_test"

g_pass=0
g_fail=0

ok() {
    printf 'PASS: %s\n' "$1"
    g_pass=$((g_pass + 1))
}

bad() {
    printf 'FAIL: %s\n' "$1"
    g_fail=$((g_fail + 1))
}

expect_file() {
    if [ -f "$1" ]; then
        ok "installed: ${1#$PKG/}"
    else
        bad "missing file: ${1#$PKG/}"
    fi
}

echo "[layout] package folder: $PKG"

if [ ! -d "$EXT_DIR" ]; then
    bad "Pd externals directory missing: lib/pd-externals/log"
    echo "[layout] tree of $PKG:"
    find "$PKG" -maxdepth 4 | head -40
    echo "[test] $g_pass passed, $g_fail failed"
    exit 1
fi
ok "Pd externals directory present: lib/pd-externals/log"

# --- the five externals ------------------------------------------------------
for obj in logpost debug normal error fatal; do
    expect_file "$EXT_DIR/$obj.pd_linux"
done

# --- their help patches ------------------------------------------------------
for obj in logpost debug normal error fatal; do
    expect_file "$EXT_DIR/$obj-help.pd"
done

# --- library metadata and documentation --------------------------------------
expect_file "$EXT_DIR/log-meta.pd"
expect_file "$EXT_DIR/README.txt"
expect_file "$EXT_DIR/LICENSE.txt"
expect_file "$PKG/licenses/LICENSE.txt"

if grep -q '^#X text [0-9][0-9]* [0-9][0-9]* VERSION 0\.1;' \
        "$EXT_DIR/log-meta.pd" 2>/dev/null; then
    ok "log-meta.pd declares VERSION 0.1"
else
    bad "log-meta.pd does not declare VERSION 0.1"
fi

# --- native load of every external -------------------------------------------
if [ ! -x "$NATIVE_TEST" ]; then
    bad "native test binary not built: $NATIVE_TEST"
else
    ok "native test binary built"
    if "$NATIVE_TEST" "$EXT_DIR"; then
        ok "all externals dlopen and export their Pd setup entry point"
    else
        bad "native dlopen/dlsym test reported failures"
    fi
fi

echo "[test] $g_pass passed, $g_fail failed"
[ "$g_fail" -eq 0 ]
