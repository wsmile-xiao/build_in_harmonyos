#!/bin/sh
# test.sh — Smoke test for shpotify 2.1
# POSIX sh (no bashisms): CI workers may set SHELL=/bin/sh, which on OHOS is
# toybox/ash, NOT bash. So this file must boot under /bin/sh, then locate a
# REAL bash to actually execute the shpotify script.
set -eu

# spotify command (bin dir passed as the first argument)
SHPOTIFY_BIN_DIR="$1"
SHPOTIFY="$SHPOTIFY_BIN_DIR/spotify"

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
    echo "FAIL: no real bash found (shpotify requires Bash)" >&2
    exit 1
}

export PATH="$SHPOTIFY_BIN_DIR:$(dirname "$BASH_PATH"):/data/service/hnp/bin:/usr/local/bin:/bin:/usr/bin:$PATH"

# Test 1: `spotify` with no arguments must print usage and exit 0.
# (This is the only upstream entry point that does not require the macOS
# Spotify desktop app; verified: bash spotify -> "Usage:" + exit 0.)
output="$("$BASH_PATH" "$SHPOTIFY" 2>&1)" || true
echo "Test 1 (spotify no-args, exit=$?): $(echo "$output" | head -1)"
printf '%s\n' "$output" | grep -q "Usage:" || {
    echo "FAIL: expected 'Usage:' in no-args output" >&2
    exit 1
}
printf '%s\n' "$output" | grep -qi "spotify <command>" || {
    echo "FAIL: expected 'spotify <command>' usage line" >&2
    exit 1
}

# Test 2: Bash syntax check of the packaged script.
"$BASH_PATH" -n "$SHPOTIFY" || {
    echo "FAIL: bash -n syntax check failed" >&2
    exit 1
}

# Test 3: the packaged script is executable and shebang is bash.
[ -x "$SHPOTIFY" ] || {
    echo "FAIL: spotify is not executable" >&2
    exit 1
}
head -1 "$SHPOTIFY" | grep -q "#!/usr/bin/env bash" || {
    echo "FAIL: unexpected shebang" >&2
    exit 1
}

echo "All shpotify tests PASSED"
