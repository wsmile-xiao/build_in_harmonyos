#!/bin/sh
# authselect CLI consumer test — runs inside the Conan test_package context.
# Locates the installed authselect binary via PATH (conanrun env puts the
# package bin dir first), then verifies observable CLI behavior.
set -u

fail() {
    echo "FAIL: $*" >&2
    exit 1
}

# 1. The installed CLI must be reachable from PATH
BIN="$(command -v authselect 2>/dev/null)" || fail "authselect CLI not found in PATH"
echo "using authselect: $BIN"
[ -x "$BIN" ] || fail "authselect binary not executable: $BIN"

# 2. --help must print the expected usage text.  popt prints help and exits
#    with a non-zero POPT_ERROR_HELP code, so assert on the output content.
HELP_OUT="$("$BIN" --help 2>&1)"
echo "$HELP_OUT" | grep -q "Available commands" || fail "--help output missing 'Available commands' (got: $HELP_OUT)"

# 3. Usage header identifies the authselect executable (popt CLI has no
#    --version option; it prints a usage banner instead).
echo "$HELP_OUT" | grep -q "^Usage:" || fail "usage banner missing (got: $HELP_OUT)"
echo "PASS: authselect CLI verified: $BIN"
exit 0