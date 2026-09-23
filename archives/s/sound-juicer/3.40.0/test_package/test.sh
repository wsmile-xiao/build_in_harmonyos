#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for the sound-juicer binary.
#
# sound-juicer is a GNOME CD ripper. With HAVE_STUB_DEPS it compiles and its
# GApplication handles --help before any UI initialization, so the smoke
# test verifies:
#   1. the binary is installed and is a valid ELF
#   2. after OHOS self-signing (unsigned binaries cannot execute), it runs
#      and prints the GApplication usage text
set -uo pipefail

# Locate the binary (conanrun.sh puts the package bindir on PATH)
SJ_BIN="$(command -v sound-juicer || true)"
if [ -z "$SJ_BIN" ] || [ ! -x "$SJ_BIN" ]; then
  echo "FAIL: sound-juicer binary not found"
  exit 1
fi
echo "PASS: sound-juicer binary found at $SJ_BIN"

# Verify it's a valid ELF binary
if [ "$(head -c 4 "$SJ_BIN")" != "$(printf '\177ELF')" ]; then
  echo "FAIL: $SJ_BIN is not an ELF binary"
  exit 1
fi
echo "PASS: sound-juicer is a valid ELF binary"

# OHOS blocks execution of unsigned binaries; sign a copy for the smoke test
SIGNER="/data/service/hnp/bin/binary-sign-tool"
TEST_BIN="$(dirname "$0")/sj-smoke-bin"
cp "$SJ_BIN" "$TEST_BIN" || { echo "FAIL: cannot copy binary"; exit 1; }
trap 'rm -f "$TEST_BIN"' EXIT
if ! "$SIGNER" sign -inFile "$TEST_BIN" -outFile "$TEST_BIN" -selfSign 1 >/dev/null 2>&1; then
  echo "FAIL: binary-sign-tool failed to sign the test copy"
  exit 1
fi
chmod +x "$TEST_BIN"

# Run --help (handled by GApplication before any UI initialization)
echo "[test] Running sound-juicer --help"
output="$("$TEST_BIN" --help 2>&1)"
rc=$?
echo "$output" | head -5
case "$output" in
  *"Usage"*|*"Help Options"*|*"OPTION"*)
    echo "PASS: --help output contains the GApplication usage text"
    ;;
  *)
    echo "FAIL: --help produced unexpected output (rc=$rc)"
    exit 1
    ;;
esac

echo "test sound-juicer 3.40.0: OK"
