#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "usage: $0 <path-to-algolia>" >&2
    exit 2
fi

algolia_bin="$1"

if [ ! -f "$algolia_bin" ]; then
    echo "algolia binary not found: $algolia_bin" >&2
    exit 1
fi

echo "[step] Testing 'algolia --version'..."
version_output="$("$algolia_bin" --version 2>&1)"
echo "version output: $version_output"
printf '%s\n' "$version_output" | grep -F "1.14.0" >/dev/null
echo "        [ok] version check passed (1.14.0 embedded via ldflags)"

echo "[step] Testing 'algolia --help'..."
help_output="$("$algolia_bin" --help 2>&1)"
echo "$help_output" | grep -F "The official command-line tool to interact with Algolia" >/dev/null
echo "        [ok] help check passed (usage output)"

echo "[step] Testing 'algolia auth --help'..."
"$algolia_bin" auth --help >/dev/null 2>&1
echo "        [ok] subcommand help check passed"

echo "[ok] All tests passed."
