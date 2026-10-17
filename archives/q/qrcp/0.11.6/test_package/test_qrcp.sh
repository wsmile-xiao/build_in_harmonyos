#!/usr/bin/env bash
# test_package/test_qrcp.sh — consumer smoke test for the packaged `qrcp` binary.
#
# Asserts (6 cases):
#   1. `qrcp version` exits 0
#   2. `qrcp version` output contains "qrcp 0.11.6"
#   3. `qrcp --help` exits 0
#   4. `--help` lists the `send` sub-command
#   5. `--help` lists the `receive` sub-command
#   6. [HarmonyOS-specific] the packaged ELF is OHOS-signed (.codesign section),
#      which is required before the HarmonyOS kernel will exec the binary.
set -euo pipefail

# HMBS injects TMPDIR/TMP/TEMP; cd there so the shell is not left in an HMDFS cwd
# that breaks getcwd (`[shell_getcwd]` diagnostic).
cd "${TMPDIR:-${TMP:-${TEMP:-/tmp}}}" 2>/dev/null || cd /tmp 2>/dev/null || true

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
    echo "usage: $0 <path-to-qrcp> [expect-codesign 0|1]" >&2
    exit 2
fi

qrcp_bin="$1"
expect_codesign="${2:-0}"

if [ ! -f "$qrcp_bin" ]; then
    echo "qrcp binary not found: $qrcp_bin" >&2
    exit 1
fi

echo "[step 1/6] Testing qrcp version..."
version_output="$("$qrcp_bin" version 2>&1)"
echo "version output: $version_output"
printf '%s\n' "$version_output" | grep -F "qrcp 0.11.6" >/dev/null
echo "        [ok] qrcp version exits 0 and reports 0.11.6"

echo "[step 2/6] Testing qrcp --help..."
help_output="$("$qrcp_bin" --help 2>&1)"
printf '%s\n' "$help_output" | grep -E '^[[:space:]]+send' >/dev/null
printf '%s\n' "$help_output" | grep -E '^[[:space:]]+receive' >/dev/null
echo "        [ok] help lists send and receive sub-commands"

if [ "$expect_codesign" = "1" ]; then
    echo "[step 3/6] Testing HarmonyOS ELF signature (.codesign)..."
    readelf_bin="$(command -v readelf || echo /data/service/hnp/bin/readelf)"
    if [ -x "$readelf_bin" ]; then
        "$readelf_bin" -S "$qrcp_bin" | grep -F ".codesign" >/dev/null
    else
        grep -a -F ".codesign" "$qrcp_bin" >/dev/null
    fi
    echo "        [ok] qrcp ELF carries the OHOS .codesign section (executable on HarmonyOS)"
else
    echo "[step 3/6] OHOS signature check skipped (target os is not OHOS)"
fi

echo "[ok] All tests passed."
