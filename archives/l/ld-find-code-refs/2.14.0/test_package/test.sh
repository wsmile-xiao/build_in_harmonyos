#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "usage: $0 <path-to-ld-find-code-refs>" >&2
    exit 2
fi

ldfcr_bin="$1"

if [ ! -f "$ldfcr_bin" ]; then
    echo "ld-find-code-refs binary not found: $ldfcr_bin" >&2
    exit 1
fi

echo "[step] Testing 'ld-find-code-refs --version'..."
version_output="$("$ldfcr_bin" --version 2>&1)"
echo "version output: $version_output"
printf '%s\n' "$version_output" | grep -F "ld-find-code-refs" >/dev/null
printf '%s\n' "$version_output" | grep -F "2.14.0" >/dev/null
echo "        [ok] version check passed (internal/version.Version const = 2.14.0 baked at link time)"

echo "[step] Testing 'ld-find-code-refs --help'..."
help_output="$("$ldfcr_bin" --help 2>&1)"
printf '%s\n' "$help_output" | grep -F "prune" >/dev/null
echo "        [ok] help check passed (subcommands listed)"

echo "[step] Negative check: 'ld-find-code-refs prune' without arguments must be rejected..."
if "$ldfcr_bin" prune >/dev/null 2>&1; then
    echo "        [fail] 'prune' without args unexpectedly succeeded" >&2
    exit 1
fi
echo "        [ok] cobra arg validation rejects 'prune' with no branch arguments (non-zero exit)"

echo "[ok] All tests passed."
