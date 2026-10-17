#!/usr/bin/env bash
set -euo pipefail

MGITSTATUS="$1"

version_output=$("$MGITSTATUS" --version)
case "$version_output" in
    v2.3) echo "OK: version $version_output" ;;
    *) echo "FAIL: unexpected version output: $version_output" >&2; exit 1 ;;
esac

TEST_ROOT=$(mktemp -d "${TMPDIR:-$HOME}/mgitstatus-test.XXXXXX")
trap 'rm -rf "$TEST_ROOT"' EXIT
REPO="$TEST_ROOT/repo"
mkdir -p "$REPO"
git -C "$REPO" init -q
git -C "$REPO" config user.email test@example.com
git -C "$REPO" config user.name mgitstatus-test
printf 'base\n' > "$REPO/tracked.txt"
git -C "$REPO" add tracked.txt
git -C "$REPO" commit -qm initial
printf 'modified\n' >> "$REPO/tracked.txt"

export GIT_CONFIG_COUNT=1
export GIT_CONFIG_KEY_0=safe.directory
export GIT_CONFIG_VALUE_0="$REPO"
scan_output=$("$MGITSTATUS" "$REPO" 2>&1)
case "$scan_output" in
    *"Uncommitted changes"*) echo "OK: detected uncommitted changes" ;;
    *) echo "FAIL: scan did not report uncommitted changes: $scan_output" >&2; exit 1 ;;
esac

echo "ALL TESTS PASSED"
