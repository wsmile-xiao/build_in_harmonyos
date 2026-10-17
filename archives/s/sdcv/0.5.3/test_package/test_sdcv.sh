#!/bin/sh
# Consumer test: run the installed sdcv binary and assert real behavior.
set -e

SDCV="$1"

if [ ! -x "$SDCV" ]; then
    echo "sdcv binary not found or not executable: $SDCV" >&2
    exit 1
fi

# 1) --help exits 0 and prints the tool banner
"$SDCV" --help | grep -q "sdcv"

# 2) unknown option is rejected with a non-zero exit code
if "$SDCV" --definitely-not-an-option >/dev/null 2>&1; then
    echo "sdcv accepted an unknown option, behavior changed" >&2
    exit 1
fi

echo "test_sdcv: behavior assertions passed"
