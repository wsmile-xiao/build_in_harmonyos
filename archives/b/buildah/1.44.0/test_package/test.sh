#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for the buildah executable.
# R34: genuinely exercises the packaged binary by running it.
#
# With the 0003 syscall-probe patch applied, `buildah --version` runs cleanly
# on HarmonyOS (the pre-patch binary died with SIGSYS from the open_tree(2)
# probe). This test therefore requires a real successful execution — a SIGSYS
# crash is treated as a defect, not as a "known platform limitation".
#
# Rootless container storage (images/from/build) needs user namespaces that
# the HarmonyOS kernel denies; commands beyond --version/--help are not
# exercised here — see notes.md "Known platform limitation".
set -euo pipefail

BUILDAH_PATH=$(command -v buildah 2>/dev/null || true)
if [ -z "$BUILDAH_PATH" ]; then
    echo "FAIL: buildah not found in PATH"
    exit 1
fi
echo "[test] buildah found at: $BUILDAH_PATH"

# HarmonyOS: containers/storage GetRuntimeDir() checks that the fallback
# $TMPDIR/storage-run-<uid> dir is "writable only by owner"; HMDFS chmod
# semantics (E046) make that check fail. A non-empty XDG_RUNTIME_DIR
# short-circuits that check entirely. Use the ext2 partition (real 0700)
# when XDG_RUNTIME_DIR is unset and the partition exists; Linux CI hosts
# with a normal /run/user/<uid> are unaffected.
if [ -z "${XDG_RUNTIME_DIR:-}" ] && [ -d /data/storage/el2/base/haps/entry/files ]; then
    XDG_RUNTIME_DIR=/data/storage/el2/base/haps/entry/files
    export XDG_RUNTIME_DIR
fi

# Verify ELF + AArch64 via Python (portable, no external deps)
python3 -c "
import sys
data = open('$BUILDAH_PATH', 'rb').read(64)
if data[:4] != b'\x7fELF':
    print('FAIL: not ELF', file=sys.stderr)
    sys.exit(1)
# e_machine at offset 18 (2 bytes, little-endian)
machine = int.from_bytes(data[18:20], 'little')
if machine != 183:  # EM_AARCH64
    print(f'FAIL: not AArch64 (machine={machine})', file=sys.stderr)
    sys.exit(1)
print('[test] ELF AArch64: OK')
" || exit 1

# Run the binary (R34: must exercise the actual binary).
# Use mktemp for the stderr capture file so concurrent test_package runs of
# this package cannot overwrite each other's temp files.
set +e
_ERRFILE=$(mktemp "${TMPDIR:-/data/storage/el2/base/haps/entry/files}/buildah_test_XXXXXX") || {
    echo "FAIL: cannot create temp file for stderr capture"
    exit 1
}
buildah --version 2>"$_ERRFILE"
EXIT_CODE=$?
STDERR_OUTPUT=$(cat "$_ERRFILE" 2>/dev/null || echo "")
# rm guarded: the temp file may already be gone if TMPDIR was cleaned up
rm -f "$_ERRFILE" 2>/dev/null || true
set -e

if [ "$EXIT_CODE" -eq 0 ]; then
    echo "[test] buildah --version succeeded"
    exit 0
fi

# Any failure is a real defect: report stderr for diagnosis.
echo "FAIL: buildah --version failed (exit=$EXIT_CODE)"
echo "stderr: $STDERR_OUTPUT"
case "$STDERR_OUTPUT" in
    *SIGSYS*|*"bad system call"*)
        echo "[test] SIGSYS indicates the syscall-probe patch (0003) is missing or ineffective"
        ;;
esac
exit 1
