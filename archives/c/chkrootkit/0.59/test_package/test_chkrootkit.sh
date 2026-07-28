#!/bin/bash
# Verify the packaged chkrootkit wrapper and selected helper binaries.

set -euo pipefail

CHKROOTKIT_BIN="$1"
TEST_SHELL="$2"

if [ -z "$CHKROOTKIT_BIN" ] || [ -z "$TEST_SHELL" ]; then
    echo "ERROR: chkrootkit binary path and shell path are required"
    exit 1
fi

if [ ! -x "$CHKROOTKIT_BIN" ]; then
    echo "ERROR: $CHKROOTKIT_BIN not found or not executable"
    exit 1
fi

pkg_root="$(CDPATH= cd -- "$(dirname -- "$CHKROOTKIT_BIN")/.." && pwd)"
libexec="$pkg_root/libexec/chkrootkit"

for tool in chkrootkit chklastlog chkwtmp chkproc chkdirs check_wtmpx strings-static chkutmp; do
    if [ ! -x "$libexec/$tool" ]; then
        echo "ERROR: missing executable $tool"
        exit 1
    fi
done

set +e
output=$("$TEST_SHELL" "$CHKROOTKIT_BIN" -V 2>&1)
version_status=$?
set -e

if [ "$version_status" -gt 1 ]; then
    echo "ERROR: chkrootkit version command failed with status $version_status"
    printf "%s\n" "$output"
    exit 1
fi

case "$output" in
    *"chkrootkit version 0.59"*)
        printf "%s\n" "$output"
        ;;
    *)
        echo "ERROR: unexpected chkrootkit version output"
        printf "%s\n" "$output"
        exit 1
        ;;
esac

tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT
mkdir "$tmpdir/visible"
if ! "$libexec/chkdirs" "$tmpdir" >/dev/null; then
    echo "ERROR: chkdirs failed to inspect the temporary directory"
    exit 1
fi

strings_output=$("$libexec/strings-static" "$libexec/chkrootkit")
case "$strings_output" in
    *"chkrootkit"*)
        ;;
    *)
        echo "ERROR: strings-static did not inspect the chkrootkit script"
        exit 1
        ;;
esac

echo "PASS: chkrootkit wrapper and helper binaries passed smoke tests"
exit 0
