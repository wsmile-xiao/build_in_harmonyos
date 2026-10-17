#!/usr/bin/env bash
# test_package/test.sh — smoke test for the diffpdf executable.
# Runs in conanrun env (PATH includes installed bin/).
# R34/R40: link-level + CLI-level verification of the Qt5 GUI app:
# `diffpdf --help` constructs QApplication, parses arguments and
# prints usage, returning 0 (see main.cpp --help branch).
set -euo pipefail

# No display on OHOS: use the offscreen platform plugin from qt5-qtbase.
export QT_QPA_PLATFORM=offscreen

echo "[test] diffpdf --help"
out=$(diffpdf --help 2>&1) || {
    rc=$?
    echo "❌ diffpdf --help exited $rc"
    exit 1
}

echo "$out" | grep -qi "usage: diffpdf" || {
    echo "❌ --help output missing usage banner"
    exit 1
}
echo "$out" | grep -qi "compares two PDF files" || {
    echo "❌ --help output missing description line"
    exit 1
}
echo "$out" | grep -q -- "--appearance" || {
    echo "❌ --help output missing --appearance option"
    exit 1
}
echo "$out" | grep -q -- "--words" || {
    echo "❌ --help output missing --words option"
    exit 1
}
echo "✅ diffpdf --help OK (QApplication init + usage output verified)"
