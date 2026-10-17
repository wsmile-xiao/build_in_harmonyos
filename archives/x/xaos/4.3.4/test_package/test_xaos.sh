#!/usr/bin/env bash
# Runs the HarmonyOS native XaoS rendering consumer test.
set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "        [fail] Usage: $0 <package-root>" >&2
    exit 2
fi

PACKAGE_ROOT=$(cd "$1" && pwd)
XAO_BINARY="$PACKAGE_ROOT/bin/XaoS"
FIXTURE="$(cd "$(dirname "$0")" && pwd)/xaos-smoke.xaf"

if [ ! -x "$XAO_BINARY" ]; then
    echo "        [fail] XaoS executable is missing or not executable: $XAO_BINARY" >&2
    exit 1
fi

TMP_ROOT="${TMPDIR:-${HOME:-/tmp}}"
mkdir -p "$TMP_ROOT"
TEST_TMP=$(mktemp -d "$TMP_ROOT/xaos-render.XXXXXX")
trap 'rm -rf "$TEST_TMP"' EXIT

echo "[step] Running native XaoS renderer on $(uname -srm)"
echo "[step] Input: $FIXTURE"
echo "[step] Output: $TEST_TMP/frame-000000.png"
(
    cd "$PACKAGE_ROOT"
    QT_QPA_PLATFORM=offscreen timeout 60 "$XAO_BINARY" \
        -render "$FIXTURE" \
        -basename "$TEST_TMP/frame-" \
        -size 160x120 \
        -renderframerate 1
)

PNG="$TEST_TMP/frame-000000.png"
if [ ! -s "$PNG" ]; then
    echo "        [fail] XaoS did not create a non-empty first frame: $PNG" >&2
    exit 1
fi

python3 "$(dirname "$0")/verify_png.py" "$PNG" 160 120
echo "        [ok] XaoS generated and decoded a non-uniform 160x120 Mandelbrot frame"
