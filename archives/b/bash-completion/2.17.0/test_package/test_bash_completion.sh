#!/bin/sh
# test_package/test_bash_completion.sh
# Verifies bash-completion package content is installed correctly
set -e

BC_ROOT="${1:-}"

if [ -z "$BC_ROOT" ]; then
    echo "Usage: $0 <package_root>"
    exit 1
fi

BC_SHARE="$BC_ROOT/share/bash-completion"
BC_SCRIPT="$BC_SHARE/bash_completion"

# Check main script exists
if [ ! -f "$BC_SCRIPT" ]; then
    echo "FAIL: bash_completion script not found at $BC_SCRIPT"
    exit 1
fi

# Check completions directory
if [ ! -d "$BC_SHARE/completions" ]; then
    echo "FAIL: completions directory not found"
    exit 1
fi

COMPLETION_COUNT=$(ls "$BC_SHARE/completions" | wc -l)
if [ "$COMPLETION_COUNT" -lt 100 ]; then
    echo "FAIL: expected 100+ completions, got $COMPLETION_COUNT"
    exit 1
fi

# Check helpers directory
if [ ! -d "$BC_SHARE/helpers" ]; then
    echo "FAIL: helpers directory not found"
    exit 1
fi

echo "PASS: bash-completion package verified ($COMPLETION_COUNT completions)"
