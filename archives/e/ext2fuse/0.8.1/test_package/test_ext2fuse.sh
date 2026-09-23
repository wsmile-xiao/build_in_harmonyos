#!/bin/sh
# Consumer test for the installed ext2fuse executable.
set -eu

if [ "$#" -lt 2 ]; then
    echo "usage: $0 <bin_dir> <work_dir>" >&2
    exit 2
fi

BIN_DIR="$1"
WORK_DIR="$2"
EXT2FUSE="$BIN_DIR/ext2fuse"

if [ ! -x "$EXT2FUSE" ]; then
    echo "FAIL: ext2fuse is not executable: $EXT2FUSE" >&2
    exit 1
fi

mkdir -p "$WORK_DIR"

set +e
"$EXT2FUSE" --version >"$WORK_DIR/ext2fuse-version.txt" 2>&1
VERSION_RC=$?
set -e
if [ "$VERSION_RC" -ne 9 ] || ! grep -q "ext2fuse version 0.8.1" "$WORK_DIR/ext2fuse-version.txt"; then
    echo "FAIL: --version did not return the expected CLI result" >&2
    cat "$WORK_DIR/ext2fuse-version.txt" >&2
    exit 1
fi

set +e
"$EXT2FUSE" --help >"$WORK_DIR/ext2fuse-help.txt" 2>&1
HELP_RC=$?
set -e
if [ "$HELP_RC" -ne 9 ] || ! grep -q "ext2fuse devicename mountpoint" "$WORK_DIR/ext2fuse-help.txt"; then
    echo "FAIL: --help did not return the expected usage result" >&2
    cat "$WORK_DIR/ext2fuse-help.txt" >&2
    exit 1
fi

set +e
"$EXT2FUSE" >"$WORK_DIR/ext2fuse-no-args.txt" 2>&1
NO_ARGS_RC=$?
set -e
if [ "$NO_ARGS_RC" -eq 0 ] || ! grep -q "ext2fuse devicename mountpoint" "$WORK_DIR/ext2fuse-no-args.txt"; then
    echo "FAIL: missing-argument path did not return usage" >&2
    cat "$WORK_DIR/ext2fuse-no-args.txt" >&2
    exit 1
fi

echo "PASS: ext2fuse executable and argument parsing"
