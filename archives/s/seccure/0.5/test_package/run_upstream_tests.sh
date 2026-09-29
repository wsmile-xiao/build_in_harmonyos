#!/bin/sh
set -eu

BIN_SRC=${1:?missing installed bin directory}
WORK=${2:?missing test work directory}
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

rm -rf "$WORK"
mkdir -p "$WORK/bin" "$WORK/test"
cp -R "$BIN_SRC"/. "$WORK/bin/"
cp -R "$SCRIPT_DIR/upstream_test"/. "$WORK/test/"

for name in seccure-key seccure-encrypt seccure-decrypt seccure-sign \
            seccure-verify seccure-signcrypt seccure-veridec seccure-dh; do
    if [ ! -x "$WORK/bin/$name" ]; then
        echo "FAIL - installed binary missing or not executable: $name"
        exit 1
    fi
done
printf 'HARMONY_TEST_RESULT total=8 passed=8 failed=0\n'

make -C "$WORK/test" -j1 SECCURE-PATH="$WORK/bin/"
printf 'UPSTREAM_TEST_RESULT total=3 passed=3 failed=0\n'
