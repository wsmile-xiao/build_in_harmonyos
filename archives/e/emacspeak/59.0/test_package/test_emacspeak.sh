#!/usr/bin/env bash
# R34: real smoke test for emacspeak 59.0 — exercises the packaged artifact.
# Emacspeak is an Emacs Lisp extension package (no compiled binaries).
# We verify presence and integrity of key .el files, server scripts,
# and directory structure.
set -uo pipefail

SHARE_DIR="${1:?usage: test_emacspeak.sh <package share dir>}"

FAIL=0

# --- Key Lisp files must exist and be non-empty ---
LISP_DIR="$SHARE_DIR/lisp"
for f in emacspeak-setup.el emacspeak.el emacspeak-loaddefs.el emacspeak-preamble.el; do
    if [ ! -s "$LISP_DIR/$f" ]; then
        echo "FAIL: $f missing or empty in $LISP_DIR"
        FAIL=1
    fi
done

# --- Count .el files (expect >= 200) ---
EL_COUNT=$(find "$LISP_DIR" -name "*.el" -type f 2>/dev/null | wc -l)
if [ "$EL_COUNT" -lt 200 ]; then
    echo "FAIL: expected >= 200 .el files, found $EL_COUNT"
    FAIL=1
fi

# --- Servers directory must exist with scripts ---
SERVERS_DIR="$SHARE_DIR/servers"
if [ ! -d "$SERVERS_DIR" ]; then
    echo "FAIL: servers directory missing"
    FAIL=1
else
    for f in speech-server espeak dtk-soft outloud; do
        if [ ! -f "$SERVERS_DIR/$f" ]; then
            echo "FAIL: server script $f missing in $SERVERS_DIR"
            FAIL=1
        fi
    done
fi

# --- etc directory with utilities ---
ETC_DIR="$SHARE_DIR/etc"
if [ ! -d "$ETC_DIR" ]; then
    echo "FAIL: etc directory missing"
    FAIL=1
fi

# --- sounds directory ---
SOUNDS_DIR="$SHARE_DIR/sounds"
if [ ! -d "$SOUNDS_DIR" ]; then
    echo "FAIL: sounds directory missing"
    FAIL=1
fi

if [ "$FAIL" -eq 0 ]; then
    echo "emacspeak smoke test: OK ($EL_COUNT .el files verified)"
fi
exit "$FAIL"
