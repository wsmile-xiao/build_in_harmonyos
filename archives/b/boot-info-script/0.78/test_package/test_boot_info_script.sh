#!/bin/bash
# Verify the packaged bootinfoscript wrapper and core CLI behaviors.

set -euo pipefail

BIN="${1:-}"
TEST_SHELL="${2:-}"

if [ -z "$BIN" ] || [ -z "$TEST_SHELL" ]; then
    echo "[fail] bootinfoscript binary path and shell path are required"
    exit 1
fi

if [ ! -x "$BIN" ]; then
    echo "[fail] $BIN not found or not executable"
    exit 1
fi

if [ ! -x "$TEST_SHELL" ]; then
    echo "[fail] $TEST_SHELL not found or not executable"
    exit 1
fi

pkg_root="$(CDPATH= cd -- "$(dirname -- "$BIN")/.." && pwd)"

# Core assertions (1-6): aligned with notes.md and MANIFEST assertion_count=6.
# (wrapper/shell executability checks above are preflight validation, not counted.)

# 1. libexec/boot-info-script/bootinfoscript is installed
if [ ! -f "$pkg_root/libexec/boot-info-script/bootinfoscript" ]; then
    echo "[fail] missing libexec/boot-info-script/bootinfoscript"
    exit 1
fi

# 2. --version prints the upstream version string
version_output="$("$TEST_SHELL" "$BIN" --version)"
printf "%s\n" "$version_output" | grep -F "version: 0.78"

# 3. -v alias prints the same version block
v_output="$("$TEST_SHELL" "$BIN" -v)"
printf "%s\n" "$v_output" | grep -F "version: 0.78"

# 4. --help prints the usage banner
help_output="$("$TEST_SHELL" "$BIN" --help)"
printf "%s\n" "$help_output" | grep -F "Usage Boot Info Script"

# 5. -h alias prints the same help banner
h_output="$("$TEST_SHELL" "$BIN" -h)"
printf "%s\n" "$h_output" | grep -F "Usage Boot Info Script"

# 6. PATH lookup resolves the wrapper and still reports the version
path_output="$(cd "$pkg_root" && PATH="$pkg_root/bin:$PATH" "$TEST_SHELL" -c 'bootinfoscript --version')"
printf "%s\n" "$path_output" | grep -F "version: 0.78"

echo "[ok] bootinfoscript wrapper, PATH lookup, version output, and help output are valid"
