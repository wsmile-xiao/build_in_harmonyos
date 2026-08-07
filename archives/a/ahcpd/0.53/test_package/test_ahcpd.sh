#!/data/service/hnp/bin/bash
set -euo pipefail

AHCPD="${1:-ahcpd}"

set +e
OUTPUT="$("$AHCPD" 2>&1)"
RC=$?
set -e

if [ "$RC" -ne 1 ]; then
    echo "FAIL: expected ahcpd without interfaces to return 1, got $RC" >&2
    echo "$OUTPUT" >&2
    exit 1
fi

printf '%s\n' "$OUTPUT" | grep -q 'Syntax: ahcpd'
printf '%s\n' "$OUTPUT" | grep -q 'interface'

echo "ahcpd usage smoke test: PASS"
