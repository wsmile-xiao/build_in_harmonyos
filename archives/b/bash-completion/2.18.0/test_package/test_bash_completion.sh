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

# Check completions directories.
# bash-completion >= 2.18 splits completions into completions-core/
# and completions-fallback/ (the legacy completions/ dir only holds
# README.md). Count all three.
COMPLETION_COUNT=0
for sub in completions-core completions-fallback completions; do
    if [ -d "$BC_SHARE/$sub" ]; then
        n=$(ls "$BC_SHARE/$sub" | wc -l)
        COMPLETION_COUNT=$((COMPLETION_COUNT + n))
    fi
done

if [ "$COMPLETION_COUNT" -lt 100 ]; then
    echo "FAIL: expected 100+ completions across completions-core/"
    echo "      completions-fallback/completions, got $COMPLETION_COUNT"
    exit 1
fi

# Check helpers directory
if [ ! -d "$BC_SHARE/helpers" ]; then
    echo "FAIL: helpers directory not found"
    exit 1
fi

echo "PASS: bash-completion package verified ($COMPLETION_COUNT completions)"
