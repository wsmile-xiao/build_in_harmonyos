#!/bin/sh
# Exercise every command shipped by the iputils package without requiring
# network access or elevated raw-socket privileges.
set -eu

PACKAGE_FOLDER="$1"
TMPDIR="${TMPDIR:-$HOME/tmp}"
TEST_DIR="$TMPDIR/iputils-conan-test-$$"

mkdir -p "$TEST_DIR"
trap 'rm -rf "$TEST_DIR"' EXIT HUP INT TERM

for command in ping tracepath arping clockdiff; do
    source_bin="$PACKAGE_FOLDER/bin/$command"
    test_bin="$TEST_DIR/$command"

    if [ ! -f "$source_bin" ]; then
        echo "ERROR: missing packaged command: $source_bin" >&2
        exit 1
    fi

    # Re-copying to a writable location also handles HMDFS execution labels.
    cp "$source_bin" "$test_bin"
    chmod 755 "$test_bin"
    "$test_bin" -V
done
