#!/usr/bin/env bash
# test_mussh.sh — packaged mussh functional verification (executed by CI conan test).
# Usage: test_mussh.sh <path-to-packaged-mussh>
set -euo pipefail

MUSSH="$1"

if [ ! -f "$MUSSH" ]; then
    echo "FAIL: packaged script missing: $MUSSH" >&2
    exit 1
fi
if [ ! -x "$MUSSH" ]; then
    echo "FAIL: packaged script not executable: $MUSSH" >&2
    exit 1
fi

out=$("$MUSSH" -V) || {
    echo "FAIL: mussh -V exited non-zero" >&2
    exit 1
}
case "$out" in
    *"Version: 1.0"*)
        echo "OK: $out"
        exit 0
        ;;
    *)
        echo "FAIL: unexpected \`mussh -V\` output: $out" >&2
        exit 1
        ;;
esac
