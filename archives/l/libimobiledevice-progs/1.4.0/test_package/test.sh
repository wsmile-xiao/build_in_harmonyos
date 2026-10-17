#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for the libimobiledevice-progs tools.
# Runs in conanrun env (PATH includes the installed bin/).
# R34: genuinely exercises the tested package's binaries.
# Device-free invocations only: --version/--help print and exit 0 without a
# connected device or usbmuxd (idevice_id -l would exit non-zero without
# usbmuxd, so it is intentionally NOT used as an assertion).
set -eu

check_version() {
  local tool="$1"
  echo "[test] ${tool} --version"
  local out
  out="$("${tool}" --version)"
  echo "$out"
  case "$out" in
    *1.4.0*) echo "OK: ${tool} --version reports 1.4.0" ;;
    *) echo "FAIL: unexpected ${tool} --version output" >&2; exit 1 ;;
  esac
}

check_version idevice_id
check_version ideviceinfo
# idevicepair exercises the libplist static linkage directly (pairing records).
check_version idevicepair

echo "[test] ideviceinfo --help"
HELP_OUTPUT="$(ideviceinfo --help || true)"
echo "$HELP_OUTPUT" | head -3
case "$HELP_OUTPUT" in
  *Usage*|*usage*|*ideviceinfo*) echo "OK: ideviceinfo --help prints usage" ;;
  *) echo "FAIL: ideviceinfo --help produced no usage text" >&2; exit 1 ;;
esac
