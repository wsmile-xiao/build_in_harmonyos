#!/bin/sh
# test_package/test_gnu_typist.sh - smoke test for gnu-typist CLI
set -eu

echo "[test] gtypist --version"
VERSION_OUTPUT="$(gtypist --version 2>&1)"
echo "$VERSION_OUTPUT"
case "$VERSION_OUTPUT" in
    *"GNU Typist 2.10.1"*) ;;
    *)
        echo "FAIL: unexpected gtypist version output" >&2
        exit 1
        ;;
esac

echo "[test] gtypist --help"
HELP_OUTPUT="$(gtypist --help 2>&1)"
echo "$HELP_OUTPUT" | grep -q "Usage:" || {
    echo "FAIL: gtypist --help did not print usage" >&2
    exit 1
}

echo "[test] gnu-typist smoke test: PASS"
