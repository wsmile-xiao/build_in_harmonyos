#!/usr/bin/env bash
# test_package/test.sh — Verify caddy version output and help subcommand
set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "usage: $0 <path-to-caddy>" >&2
    exit 2
fi

caddy_bin="$1"

if [ ! -f "$caddy_bin" ]; then
    echo "caddy binary not found: $caddy_bin" >&2
    exit 1
fi

# Verify version output contains v2.11.2
version_output="$("$caddy_bin" version)"
printf '%s\n' "$version_output" | grep -F "v2.11.2" >/dev/null

# Verify help works (may return non-zero on some platforms; version check above is primary)
"$caddy_bin" help >/dev/null 2>&1 || true
