#!/usr/bin/env bash
# test_package/test.sh — smoke test for the plowshare CLI suite
set -euo pipefail

TOOLS="plowdown plowup plowdel plowlist plowprobe plowmod"
VERSION_EXPECTED="2.1.7"

fail() {
    echo "[error] $*" >&2
    exit 1
}

for tool in $TOOLS; do
    command -v "$tool" >/dev/null 2>&1 || fail "$tool is not on PATH"
    [ -x "$(command -v "$tool")" ] || fail "$tool is not executable"

    bash -n "$(command -v "$tool")" || fail "$tool failed bash -n syntax check"

    version_output="$($tool --version 2>/dev/null)"
    [ "$version_output" = "$VERSION_EXPECTED" ] || fail "$tool --version expected '$VERSION_EXPECTED', got '$version_output'"

    help_output="$($tool --help 2>&1)"
    case "$help_output" in
        *"Usage:"*) : ;;
        *) fail "$tool --help did not print usage text" ;;
    esac

    echo "[ok] $tool ($($tool --version 2>/dev/null))"
done

if command -v curl >/dev/null 2>&1; then
    echo "[info] curl present: $(curl --version 2>/dev/null | head -n 1)"
else
    echo "[warn] curl not found on PATH (runtime dependency; present via Conan but not exported)"
fi

echo "[test] plowshare smoke test: PASS (6 CLIs)"