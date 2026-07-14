#!/bin/sh
# test_trans.sh — translate-shell smoke test
# Verifies that the `trans` binary is installed and can report its version.
set -euo pipefail

TRANS_BIN="$1"

if [ -z "$TRANS_BIN" ]; then
    echo "ERROR: trans binary path not provided"
    exit 1
fi

if [ ! -f "$TRANS_BIN" ]; then
    echo "ERROR: trans binary not found at $TRANS_BIN"
    exit 1
fi

# HMDFS bless: on HarmonyOS, binaries created by Conan's build
# subprocess lack execution permission. Re-copy to trigger HMDFS
# to grant exec permission.
TMPDIR="${TMPDIR:-/tmp}"
tmp="$TMPDIR/.trans_bless"
cp "$TRANS_BIN" "$tmp"
cp "$tmp" "$TRANS_BIN"
chmod 755 "$TRANS_BIN"

# Run trans --version to verify the binary works
"$TRANS_BIN" --version
