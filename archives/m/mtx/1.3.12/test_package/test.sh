#!/bin/bash
# test_package/test.sh — CLI smoke test for mtx 1.3.12
#
# MTX controls SCSI media changers, so a CI worker has no changer to talk
# to.  The assertions below therefore check the parts that are meaningful
# without hardware:
#
#   1. all five packaged tools exist and are executable;
#   2. `mtx --version` prints the version compiled in from VERSION;
#   3. `mtx noattach` (a state-only command) exits 0 without a device;
#   4. an explicit `-f <regular file>` probe fails from inside the SCSI
#      backend — proving scsi_linux.c / the SG interface was compiled in —
#      instead of failing with a path lookup error;
#   5. the other four tools print their usage text and exit 1.
#
# Usage: bash test.sh <package_folder>
#
# NOTE: bash is required for `set -o pipefail`; the OHOS profile exports
#       CONFIG_SHELL=/data/service/hnp/bin/bash, and the recipe's test()
#       launches this script through the same shell.
set -euo pipefail

PKG_DIR="${1:?usage: test.sh <package_folder>}"
BIN_DIR="$PKG_DIR/bin"

# HarmonyOS has a read-only /tmp, so pick the first writable candidate instead
# of relying on mktemp's default.
TMP_BASE=""
for candidate in "${TMPDIR:-}" "${HOME:+$HOME/tmp}" "${PWD:+$PWD/.mtx-test-tmp}"; do
    [ -n "$candidate" ] || continue
    if mkdir -p "$candidate" 2>/dev/null && [ -w "$candidate" ]; then
        TMP_BASE="$candidate"
        break
    fi
done
[ -n "$TMP_BASE" ] || { echo "FAIL: no writable temporary directory (set TMPDIR)"; exit 1; }

WORK_DIR="$(mktemp -d "${TMP_BASE%/}/mtx-test.XXXXXX")" || {
    echo "FAIL: mktemp failed under $TMP_BASE"; exit 1; }
trap 'rm -rf "$WORK_DIR"' EXIT

echo "[test] packaged tools present"
for tool in mtx tapeinfo loaderinfo scsitape scsieject; do
    test -x "$BIN_DIR/$tool" || { echo "FAIL: $tool missing or not executable in $BIN_DIR"; exit 1; }
    echo "  ok: $tool"
done

echo "[test] mtx --version"
# mtx prints its banner on stderr and calls Usage(), which exits 1.
version_out="$("$BIN_DIR/mtx" --version 2>&1 || true)"
printf '%s\n' "$version_out" | grep -q 'mtx version 1\.3\.12' || {
    echo "FAIL: unexpected version banner:"; printf '%s\n' "$version_out"; exit 1; }
echo "  ok: banner reports 1.3.12"

echo "[test] mtx noattach (state-only command, no device required)"
if ! "$BIN_DIR/mtx" noattach; then
    echo "FAIL: mtx noattach did not exit 0"
    exit 1
fi
echo "  ok: noattach succeeded without a SCSI device"

echo "[test] mtx -f <regular file> status (SCSI backend reachability)"
FAKE_DEVICE="$WORK_DIR/not-a-changer"
printf 'not a scsi generic device\n' > "$FAKE_DEVICE"
set +e
probe_out="$("$BIN_DIR/mtx" -f "$FAKE_DEVICE" status 2>&1)"
probe_rc=$?
set -e
printf '%s\n' "$probe_out"
test "$probe_rc" -eq 1 || { echo "FAIL: probe exited $probe_rc, expected 1"; exit 1; }
printf '%s\n' "$probe_out" | grep -q 'No such file' && {
    echo "FAIL: probe failed on path lookup, the SCSI backend was never reached"; exit 1; }
printf '%s\n' "$probe_out" | grep -q 'cannot open SCSI device' && {
    echo "FAIL: probe failed on open(), the SCSI backend was never reached"; exit 1; }
printf '%s\n' "$probe_out" | grep -Eq 'sg device|SCSI' || {
    echo "FAIL: probe error did not come from the SCSI backend"; exit 1; }
echo "  ok: probe reached the SCSI generic interface"

echo "[test] usage text of the remaining tools"
for tool in tapeinfo loaderinfo scsitape scsieject; do
    set +e
    usage_out="$("$BIN_DIR/$tool" --unsupported-probe 2>&1)"
    usage_rc=$?
    set -e
    test "$usage_rc" -eq 1 || { echo "FAIL: $tool exited $usage_rc, expected 1"; exit 1; }
    printf '%s\n' "$usage_out" | grep -q "Usage: $tool" || {
        echo "FAIL: $tool did not print its usage text:"; printf '%s\n' "$usage_out"; exit 1; }
    echo "  ok: $tool usage"
done

echo "OK: mtx 1.3.12 CLI smoke test passed"
