#!/bin/sh
# Consumer test: run the installed superopt binary and assert real behavior.
set -e

SUPEROPT="$1"

if [ ! -x "$SUPEROPT" ]; then
    echo "superopt binary not found or not executable: $SUPEROPT" >&2
    exit 1
fi

# 1) real synthesis run: enumerate optimal sequence for the goal function
#    lts0 ({ r = (signed_word) v0 < 0; }) -- README canonical example
OUT=$("$SUPEROPT" -flts0 -as 2>/dev/null)
case "$OUT" in
    *"found"*) : ;;
    *) echo "superopt -flts0 -as produced no synthesis result" >&2; exit 1 ;;
esac

# 2) no arguments is rejected with a non-zero exit code
if "$SUPEROPT" >/dev/null 2>&1; then
    echo "superopt accepted empty arguments, behavior changed" >&2
    exit 1
fi

# 3) unknown option is rejected with a non-zero exit code
if "$SUPEROPT" --definitely-not-an-option >/dev/null 2>&1; then
    echo "superopt accepted an unknown option, behavior changed" >&2
    exit 1
fi

echo "test_superopt: behavior assertions passed"
