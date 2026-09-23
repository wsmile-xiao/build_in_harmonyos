#!/bin/bash
# Consumer test for the units binary, run against the installed package.
# Usage: test.sh <path-to-installed definitions.units>
set -e

DEFS="$1"
if [ ! -f "$DEFS" ]; then
    echo "FAIL: definitions.units not found at: $DEFS"
    exit 1
fi

# 1. Smoke: --version exits 0.
units --version > /dev/null

# 2. Simple conversion: 1 meter -> foot, prints "* 3.2808399".
out=$(units -f "$DEFS" meter foot | head -1 | awk '{print $1}')
if [ "$out" != "*" ]; then
    echo "FAIL: meter->foot conversion failed (units -f meter foot)"
    exit 1
fi

# 3. Upstream make check expression: must evaluate to exactly 6.
chk=$(units -f "$DEFS" '(((square(kiloinch)+2.84m2) /0.5) meters^2)^(1|4)' m | head -1 | awk '{print $2}')
if [ "$chk" != "6" ]; then
    echo "FAIL: upstream check expression expected 6, got: $chk"
    exit 1
fi

echo "All tests passed"
