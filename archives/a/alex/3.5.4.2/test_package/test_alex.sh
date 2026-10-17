#!/bin/sh
# test_alex.sh — L1 test for alex 3.5.4.2
# Verifies the packaged alex binary:
#   1. binary exists
#   2. --version reports 3.5.4.2
#   3. functional: generates a lexer from a minimal .x spec (--template)
# Note: --help is NOT asserted (GHC RTS intermittently hangs on OHOS).
# set -e is intentionally omitted: the PASS/FAIL counting logic relies on
# non-zero exits from failed assertions to continue and summarize.
set -u
set -o pipefail

PASS=0
FAIL=0
ok() { echo "  ✅ $1"; PASS=$((PASS+1)); }
no() { echo "  ❌ $1"; FAIL=$((FAIL+1)); }

# Locate alex binary.
# Priority 1: ALEX_PKG_ROOT env var (passed by test_package conanfile.py).
# Priority 2: Search the Conan cache for the packaged alex binary.
ALEX=""
if [ -n "${ALEX_PKG_ROOT:-}" ] && [ -f "${ALEX_PKG_ROOT}/bin/alex" ]; then
    ALEX="${ALEX_PKG_ROOT}/bin/alex"
fi
if [ -z "$ALEX" ]; then
    ALEX=$(find "$HOME/.conan2/p" -path "*/bin/alex" -type f 2>/dev/null | head -1)
fi

echo "=== alex L1 test ==="
echo "  binary: ${ALEX:-<not found>}"

if [ -z "$ALEX" ] || [ ! -x "$ALEX" ]; then
    no "alex binary not found"
    echo ""
    echo "=== Result: PASS=$PASS FAIL=$FAIL ==="
    exit 1
fi
ok "alex binary exists"

# 1) --version (stderr suppressed so shell error text can't false-match)
VERSION_OUT=$("$ALEX" --version 2>/dev/null)
VERSION_LINE=$(echo "$VERSION_OUT" | head -1)
if echo "$VERSION_LINE" | grep -q "3.5.4.2"; then
    ok "version reports 3.5.4.2: $VERSION_LINE"
else
    no "version mismatch: $VERSION_LINE"
fi

# 2) --help is intentionally NOT asserted: on OHOS the GHC RTS intermittently
# hangs in sigsuspend when alex prints the help text and exits (observed rc=0
# and rc=124 across runs), so it would make the L1 test flaky. The substantive
# checks are --version and the functional lexer generation below.

# 3) functional: generate a lexer from a minimal .x spec.
# alex's default template dir is a build-time baked absolute datadir; use the
# packaged relocatable templates via the --template CLI override.
WORKDIR=$(mktemp -d "${TMPDIR:-/tmp}/alex-test.XXXXXX" 2>/dev/null || mktemp -d 2>/dev/null)
if [ -z "$WORKDIR" ]; then
    WORKDIR="$HOME/tmp/alex-test"
    mkdir -p "$WORKDIR"
fi
TEMPLATE_DIR=$(dirname "$ALEX")/../share/alex-3.5.4.2
cat > "$WORKDIR/Tokens.x" <<'EOF'
{
module Tokens where
}
%wrapper "basic"
$digit = 0-9
tokens :-
  $digit+ { \s -> s }
EOF
if "$ALEX" --template="$TEMPLATE_DIR" "$WORKDIR/Tokens.x" -o "$WORKDIR/Tokens.hs" 2>"$WORKDIR/alex.err"; then
    if [ -s "$WORKDIR/Tokens.hs" ]; then
        ok "generated lexer from .x spec ($(wc -c < "$WORKDIR/Tokens.hs") bytes)"
    else
        no "lexer output empty"
    fi
else
    no "alex failed on .x spec: $(head -2 "$WORKDIR/alex.err")"
fi
rm -rf "$WORKDIR"

echo ""
echo "=== Result: PASS=$PASS FAIL=$FAIL ==="
if [ "$FAIL" -gt 0 ]; then exit 1; fi
exit 0
