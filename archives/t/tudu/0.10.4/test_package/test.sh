#!/bin/sh
# test_package consumer test for tudu 0.10.4.
#
# Proves the packaged tudu CLI can be consumed end to end on this platform:
# the binary is present and executable, and `tudu --help` answers with a usage
# banner and exit code 0.
#
# Usage: test.sh [path-to-tudu-binary]
#   Defaults to `tudu` resolved from PATH (VirtualRunEnv/conanrun injects the
#   package bin/ directory). The script must be launched with bash on OHOS,
#   because /system/bin/sh (mksh) cannot exec ELF binaries.
export PATH="$PATH:/system/bin"

BIN="${1:-tudu}"

echo "--- tudu 0.10.4 consumer verification ---"

# 1. binary present (explicit path or resolvable on PATH) and executable
if [ -f "$BIN" ]; then
    :
elif command -v "$BIN" >/dev/null 2>&1; then
    BIN="$(command -v "$BIN")"
fi
[ -x "$BIN" ] || { echo "FAIL: tudu binary not found or not executable: $BIN"; exit 1; }
echo "PASS 1: binary present -> $BIN"

# 2. `--help` exits 0 and prints the usage banner
out=$("$BIN" --help 2>&1); rc=$?
if [ "$rc" != "0" ]; then
    echo "FAIL: tudu --help exit=$rc"
    printf '%s\n' "$out"
    exit 1
fi
printf '%s\n' "$out" | grep -qi "usage" || {
    echo "FAIL: unexpected --help output:"
    printf '%s\n' "$out"
    exit 1
}
echo "PASS 2: --help -> $(printf '%s\n' "$out" | head -n 1)"

echo "test tudu 0.10.4: 2/2 checks PASS"
exit 0
