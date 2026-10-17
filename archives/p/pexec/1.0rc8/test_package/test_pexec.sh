#!/bin/sh
# Consumer test: run the installed pexec binary and assert real behavior.
set -e

PEXEC="$1"

if [ ! -x "$PEXEC" ]; then
    echo "pexec binary not found or not executable: $PEXEC" >&2
    exit 1
fi

# 1) --help exits 0 and prints the tool banner
"$PEXEC" --help | grep -qi pexec

# 2) --version exits 0 and reports the program version
"$PEXEC" --version | grep -qi pexec

# 3) unknown option is rejected with a non-zero exit code
if "$PEXEC" --definitely-not-an-option >/dev/null 2>&1; then
    echo "pexec accepted an unknown option, behavior changed" >&2
    exit 1
fi

echo "test_pexec: behavior assertions passed"
