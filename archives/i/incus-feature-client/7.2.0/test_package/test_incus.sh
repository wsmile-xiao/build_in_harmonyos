#!/usr/bin/env bash
# test_package/test_incus.sh — consumer smoke test for the packaged `incus` client binary.
#
# Asserts (7 cases):
#   1. `incus --version` exits 0
#   2. `incus --version` reports the 7.2 series
#   3. `incus --help` exits 0
#   4. `--help` lists the `list` sub-command
#   5. `--help` lists the `remote` sub-command
#   6. [HarmonyOS-specific] the packaged ELF is an aarch64 ELF (OHOS/armv8 target arch)
#   7. [HarmonyOS-specific] the packaged ELF is OHOS-signed (.codesign section), which is
#      required before the HarmonyOS kernel will exec the binary.
set -euo pipefail

# HMBS injects TMPDIR/TMP/TEMP; cd there so the shell is not left in an HMDFS cwd
# that breaks getcwd (`[shell_getcwd]` diagnostic).
cd "${TMPDIR:-${TMP:-${TEMP:-/tmp}}}" 2>/dev/null || cd /tmp 2>/dev/null || true

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
    echo "usage: $0 <path-to-incus> [expect-ohos 0|1]" >&2
    exit 2
fi

incus_bin="$1"
expect_ohos="${2:-0}"

if [ ! -f "$incus_bin" ]; then
    echo "incus binary not found: $incus_bin" >&2
    exit 1
fi

echo "[case 1/7] incus --version exits 0 ..."
version_output="$("$incus_bin" --version 2>&1)"
echo "version output: $version_output"
echo "        [ok] incus --version exits 0"

echo "[case 2/7] incus --version reports the 7.2 series ..."
printf '%s\n' "$version_output" | grep -E '^7\.2' >/dev/null
echo "        [ok] version matches ^7.2"

echo "[case 3/7] incus --help exits 0 ..."
help_output="$("$incus_bin" --help 2>&1)"
printf '%s\n' "$help_output" | grep -F "Command line client for Incus" >/dev/null
echo "        [ok] incus --help exits 0"

echo "[case 4/7] --help lists the 'list' sub-command ..."
printf '%s\n' "$help_output" | grep -E '^[[:space:]]+list[[:space:]]' >/dev/null
echo "        [ok] help lists 'list'"

echo "[case 5/7] --help lists the 'remote' sub-command ..."
printf '%s\n' "$help_output" | grep -E '^[[:space:]]+remote[[:space:]]' >/dev/null
echo "        [ok] help lists 'remote'"

if [ "$expect_ohos" = "1" ]; then
    echo "[case 6/7] [HarmonyOS] packaged ELF targets aarch64 ..."
    objdump_bin="$(command -v llvm-objdump || echo /data/service/hnp/bin/llvm-objdump)"
    if [ -x "$objdump_bin" ]; then
        "$objdump_bin" -f "$incus_bin" | grep -F "aarch64" >/dev/null
    else
        # fall back to the ELF e_machine field (0xB7 = AArch64, little-endian)
        od -An -tx1 -j18 -N2 "$incus_bin" | grep -qi 'b7 00'
    fi
    echo "        [ok] ELF architecture is aarch64"

    echo "[case 7/7] [HarmonyOS] packaged ELF is OHOS-signed (.codesign) ..."
    readelf_bin="$(command -v readelf || echo /data/service/hnp/bin/readelf)"
    if [ -x "$readelf_bin" ]; then
        "$readelf_bin" -S "$incus_bin" | grep -F ".codesign" >/dev/null
    else
        grep -a -F ".codesign" "$incus_bin" >/dev/null
    fi
    echo "        [ok] ELF carries the OHOS .codesign section (executable on HarmonyOS)"
else
    echo "[case 6/7] OHOS arch check skipped (target os is not OHOS)"
    echo "[case 7/7] OHOS signature check skipped (target os is not OHOS)"
fi

echo "[ok] All tests passed."
