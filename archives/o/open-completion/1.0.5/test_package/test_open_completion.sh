#!/bin/bash
# test_package/test_open_completion.sh
# Consumer-side verification of the installed open bash completion.
set -euo pipefail

COMPLETION_FILE="${1:-}"

if [ -z "$COMPLETION_FILE" ]; then
    echo "Usage: $0 <installed completion file>"
    exit 1
fi

# 1. The completion file is installed at the documented path
if [ ! -f "$COMPLETION_FILE" ]; then
    echo "FAIL: completion file not found at $COMPLETION_FILE"
    exit 1
fi
echo "CHECK 1/6: file exists - ok"

# 2. It is non-empty (guards against empty-fixture false PASS)
if [ ! -s "$COMPLETION_FILE" ]; then
    echo "FAIL: completion file is empty: $COMPLETION_FILE"
    exit 1
fi
echo "CHECK 2/6: file non-empty - ok"

# 3. It is valid bash source
bash -n "$COMPLETION_FILE"
echo "CHECK 3/6: bash -n syntax - ok"

# 4. The upstream completion entry point is defined
if ! grep -q '_open()' "$COMPLETION_FILE"; then
    echo "FAIL: _open() is not defined"
    exit 1
fi
echo "CHECK 4/6: _open() defined - ok"

# 5. It registers the completion function for the open command
if ! grep -q 'complete.*-F _open.* open' "$COMPLETION_FILE"; then
    echo "FAIL: 'complete -F _open open' registration not found"
    exit 1
fi
echo "CHECK 5/6: complete registration present - ok"

# 6. Sourcing it (with uname stubbed to Darwin for the upstream guard)
#    actually registers the completion with bash
TMPBASE="${TMPDIR:-${TMP:-${TEMP:-/tmp}}}"
FAKEBIN="$(mktemp -d "$TMPBASE/fake-uname.XXXXXX" 2>/dev/null || mktemp -d)"
trap 'rm -rf "$FAKEBIN"' EXIT
printf '#!/bin/sh\necho Darwin\n' > "$FAKEBIN/uname"
chmod +x "$FAKEBIN/uname"
if ! PATH="$FAKEBIN:$PATH" bash --noprofile --norc -c "source '$COMPLETION_FILE' && complete -p open" | grep -q -- '-F _open'; then
    echo "FAIL: sourcing the file (as Darwin) did not register a completion for 'open'"
    exit 1
fi
echo "CHECK 6/6: source registers completion for open - ok"

echo "PASS: open-completion package verified ($COMPLETION_FILE)"
