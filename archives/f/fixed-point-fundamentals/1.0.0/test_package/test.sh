#!/bin/sh
# Consumer smoke test: run installed example binaries from package bin/.
# Covers lesson examples rendered in the installed prefix: checks exit code
# and non-empty stdout.
set -euo pipefail

fail=0

# Determine bin dir: conanrun env exposes PATH with package bin/ first.
cmd="q16_16_basics"
if command -v "$cmd" >/dev/null 2>&1; then
    out=$("$cmd" 2>&1) || { echo "FAIL: $cmd exit=$?"; fail=1; }
    [ -n "$out" ] || { echo "FAIL: $cmd produced no output"; fail=1; }
    echo "OK: $cmd ran ($(echo "$out" | wc -l) lines)"
else
    echo "FAIL: $cmd not found in PATH"; fail=1
fi

cmd="format_selector"
if command -v "$cmd" >/dev/null 2>&1; then
    out=$("$cmd" 2>&1) || { echo "FAIL: $cmd exit=$?"; fail=1; }
    [ -n "$out" ] || { echo "FAIL: $cmd produced no output"; fail=1; }
    echo "OK: $cmd ran ($(echo "$out" | wc -l) lines)"
else
    echo "FAIL: $cmd not found in PATH"; fail=1
fi

exit $fail