#!/usr/bin/env bash
set -euo pipefail

polipo_bin="$1"
www_root="$2"
expected_root="${www_root%/}/"
output=$("$polipo_bin" -v "localDocumentRoot=$www_root" 2>&1) || {
    status=$?
    printf '%s\n' "$output" >&2
    exit "$status"
}
grep -q "configFile" <<<"$output" || {
    printf '%s\n' "$output" >&2
    echo "polipo -v output did not contain configFile" >&2
    exit 2
}
grep -Fq "localDocumentRoot atom $expected_root " <<<"$output" || {
    printf '%s\n' "$output" >&2
    echo "polipo did not use the packaged localDocumentRoot" >&2
    exit 3
}
echo "test polipo 1.1.1: OK"
