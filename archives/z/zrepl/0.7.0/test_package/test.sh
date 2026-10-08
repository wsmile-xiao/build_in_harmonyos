#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "usage: $0 <path-to-zrepl>" >&2
    exit 2
fi

zrepl_bin="$1"

if [ ! -f "$zrepl_bin" ]; then
    echo "zrepl binary not found: $zrepl_bin" >&2
    exit 1
fi

echo "[step] Testing 'zrepl version --show=client'..."
version_output="$("$zrepl_bin" version --show=client 2>&1)"
echo "version output: $version_output"
printf '%s\n' "$version_output" | grep -F "zrepl version=0.7.0" >/dev/null
printf '%s\n' "$version_output" | grep -F "GOARCH=arm64" >/dev/null
echo "        [ok] version check passed (internal/version.zreplVersion var injected at link time)"

echo "[step] Testing 'zrepl --help'..."
help_output="$("$zrepl_bin" --help 2>&1)"
printf '%s\n' "$help_output" | grep -F "version" >/dev/null
printf '%s\n' "$help_output" | grep -F "configcheck" >/dev/null
echo "        [ok] help check passed (subcommands listed)"

echo "[step] Testing 'zrepl configcheck' with an empty config file..."
configcheck_tmp="./zrepl-smoke-empty-config.yml"
cleanup() { rm -f "$configcheck_tmp"; }
trap cleanup EXIT
: > "$configcheck_tmp"
"$zrepl_bin" configcheck --config "$configcheck_tmp" >/dev/null 2>&1
echo "        [ok] configcheck passed (empty job set parses; upstream's own suite parses samples/empty.yml the same way)"

echo "[step] Negative check: unknown subcommand must be rejected..."
if "$zrepl_bin" definitely-not-a-subcommand >/dev/null 2>&1; then
    echo "        [fail] unknown subcommand unexpectedly succeeded" >&2
    exit 1
fi
echo "        [ok] cobra rejects unknown subcommand (non-zero exit)"

echo "[ok] All tests passed."
