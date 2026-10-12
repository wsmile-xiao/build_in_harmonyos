#!/usr/bin/env bash
# test_package/test.sh — OHOS headless verification of the packaged vprerex
# binary, running in the conanrun environment (PATH includes the package bin).
#
# Upstream vprerex-6.5.1 has no test suite; this is the OHOS-specific test
# added by the adaptation (R34/R40/R51). No display is available on the
# worker, so the offscreen QPA platform plugin is used.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
export QT_QPA_PLATFORM=offscreen

echo "[1/3] vprerex --version"
out="$(vprerex --version 2>&1)"
printf '%s\n' "$out"
printf '%s\n' "$out" | grep -q "This is vprerex, version 6.5.1." || {
    echo "FAIL: version banner missing"
    exit 1
}

echo "[2/3] vprerex --help"
out="$(vprerex --help 2>&1)"
printf '%s\n' "$out"
printf '%s\n' "$out" | grep -q "Usage: vprerex" || {
    echo "FAIL: usage banner missing"
    exit 1
}

echo "[3/3] vprerex --check-pdf selftest.pdf (poppler-qt5 shim: load + render + links)"
out="$(vprerex --check-pdf "${HERE}/selftest.pdf" 2>&1)"
printf '%s\n' "$out"
printf '%s\n' "$out" | grep -q "vprerex-check: page=1 image=200x200" || {
    echo "FAIL: page was not rendered through the poppler-qt5 shim"
    exit 1
}
printf '%s\n' "$out" | grep -q "vprerex-check: page=1 link=coord: 3,4" || {
    echo "FAIL: link annotation was not extracted through the poppler-qt5 shim"
    exit 1
}
printf '%s\n' "$out" | grep -q "vprerex-check: ok pages=1 links=1" || {
    echo "FAIL: shim summary line missing"
    exit 1
}

echo "OK: vprerex headless smoke + poppler-qt5 shim functional check passed"
