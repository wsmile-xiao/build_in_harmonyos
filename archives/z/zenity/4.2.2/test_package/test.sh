#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for the packaged zenity executable.
# Runs in the conanrun env (PATH includes the installed bin/,
# LD_LIBRARY_PATH covers the shared gtk4/glib/libadwaita chain).
# R34: genuinely exercises the tested package's binary.
#
# --version and --help are parsed by GOption / handle-local-options
# before g_application_run, so they are safe on a headless OHOS device
# (patch 0002 makes --version skip the GTK teardown that would
# otherwise segfault without a display server). Interactive dialog
# modes require a display session and cannot run here — see
# MANIFEST.yml and notes.md for the upstream test situation.
set -eu

echo "[test] zenity --version"
OUTPUT=$(zenity --version) || {
    echo "FAIL: zenity --version exited with non-zero status"
    exit 1
}
echo "$OUTPUT"
echo "$OUTPUT" | grep -q "4.2.2" || {
    echo "FAIL: expected version 4.2.2, got: $OUTPUT"
    exit 1
}
echo "OK: zenity --version returns $OUTPUT"

echo "[test] zenity --help"
HELP_OUTPUT=$(zenity --help) || {
    echo "FAIL: zenity --help exited with non-zero status"
    exit 1
}
echo "$HELP_OUTPUT" | head -3
echo "$HELP_OUTPUT" | grep -q "Usage" || {
    echo "FAIL: zenity --help output does not contain usage text"
    exit 1
}
echo "OK: zenity --help prints usage"

echo "ALL TESTS PASSED"
