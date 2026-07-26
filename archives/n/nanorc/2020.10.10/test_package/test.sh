#!/bin/bash
# nanorc test script

set -euo pipefail

echo "Testing nanorc installation..."

if [ -z "$NANORC_PATH" ]; then
    echo "ERROR: NANORC_PATH environment variable not set"
    exit 1
fi

echo "NANORC_PATH: $NANORC_PATH"

if [ ! -d "$NANORC_PATH" ]; then
    echo "ERROR: NANORC_PATH directory does not exist: $NANORC_PATH"
    exit 1
fi

if [ ! -f "$NANORC_PATH/nanorc" ]; then
    echo "ERROR: nanorc file not found: $NANORC_PATH/nanorc"
    exit 1
fi

if [ ! -f "$NANORC_PATH/c.nanorc" ]; then
    echo "ERROR: c.nanorc file not found: $NANORC_PATH/c.nanorc"
    exit 1
fi

file_count=$(ls "$NANORC_PATH"/*.nanorc 2>/dev/null | wc -l)
echo "✓ nanorc installed successfully"
echo "✓ Total nanorc files: $file_count"

exit 0
