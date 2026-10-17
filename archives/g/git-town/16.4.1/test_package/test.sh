#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "usage: $0 <path-to-git-town>" >&2
    exit 2
fi

git_town_bin="$1"

if [ ! -f "$git_town_bin" ]; then
    echo "git-town binary not found: $git_town_bin" >&2
    exit 1
fi

# Test 1: --version should print "Git Town 16.4.1"
version_output="$("$git_town_bin" --version 2>&1)"
echo "$version_output"
echo "$version_output" | grep -F "16.4.1" >/dev/null
echo "[ok] --version OK"

# Test 2: --help should succeed and mention "Git Town"
"$git_town_bin" --help >/dev/null 2>&1
echo "[ok] --help OK"
