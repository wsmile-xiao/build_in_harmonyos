#!/bin/sh
# test.sh — Smoke test for screenfetch 3.9.9
# POSIX sh (no bashisms): CI workers invoke this via SHELL=/bin/sh, which on
# OHOS is toybox/ash, NOT bash (it rejects `set -o pipefail`, and cannot run the
# screenfetch script which is full of bashisms). So this file must boot under
# /bin/sh, then locate a REAL bash to actually execute screenfetch.
set -eu

# screenfetch command (bin dir passed as the first argument)
SCREENFETCH_BIN_DIR="$1"
SCREENFETCH="$SCREENFETCH_BIN_DIR/screenfetch"

# Locate a real bash (a shell that sets BASH_VERSION). CI may set
# CONFIG_SHELL/SHELL to /bin/sh, so those are only hints — every candidate is
# verified to actually be bash before use.
find_bash() {
    _cands="${CONFIG_SHELL:-} ${SHELL:-} /data/service/hnp/bin/bash /usr/local/bin/bash /usr/bin/bash"
    for _c in $_cands; do
        [ -n "$_c" ] || continue
        [ -x "$_c" ] || continue
        if "$_c" -c 'test -n "${BASH_VERSION:-}"' 2>/dev/null; then
            printf '%s\n' "$_c"
            return 0
        fi
    done
    _path="$(command -v bash 2>/dev/null || true)"
    if [ -n "$_path" ] && "$_path" -c 'test -n "${BASH_VERSION:-}"' 2>/dev/null; then
        printf '%s\n' "$_path"
        return 0
    fi
    return 1
}

BASH_PATH="$(find_bash)" || {
    echo "FAIL: no real bash found (screenfetch requires Bash 4.0+)" >&2
    exit 1
}

export PATH="$SCREENFETCH_BIN_DIR:$(dirname "$BASH_PATH"):/data/service/hnp/bin:/usr/local/bin:/bin:/usr/bin:$PATH"

# Test 1: screenfetch --version must print the version string.
# (`|| true' so a non-zero exit is reported via the grep rather than aborting
# under `set -e` before we can print a clear failure message.)
output="$("$BASH_PATH" "$SCREENFETCH" --version 2>&1)" || true
echo "Test 1 (screenfetch --version): $output"
printf '%s\n' "$output" | grep -q "Version 3.9.9" || {
    echo "FAIL: expected 'Version 3.9.9' in --version output" >&2
    exit 1
}

# Test 2: screenfetch --help must print usage.
output="$("$BASH_PATH" "$SCREENFETCH" --help 2>&1)" || true
echo "Test 2 (screenfetch --help): $output"
printf '%s\n' "$output" | grep -qi "usage" || {
    echo "FAIL: expected 'usage' in --help output" >&2
    exit 1
}

echo "All screenfetch tests PASSED"
