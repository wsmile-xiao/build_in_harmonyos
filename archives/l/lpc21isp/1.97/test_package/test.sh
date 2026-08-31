#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for the lpc21isp executable
# Runs in conanrun env (PATH includes the installed bin/)
# R34: genuinely exercises the tested package's binary.
#
# lpc21isp is a serial-port flash tool for NXP LPC microcontrollers.
# It has NO upstream test suite (Makefile only has all/clean targets).
#
# Hardware vs. software split (verified by source reading):
#  - HARDWARE path: main() -> ReadArguments() -> PerformActions() ->
#    OpenSerialPort() (open /dev/ttyX + termios/cfsetspeed/ioctl DTR/RTS) ->
#    ResetTarget() -> NxpDownload()/AnalogDevicesDownload() talking to a real
#    MCU. Requires a physical NXP chip + serial port. Not runnable in CI.
#    Note: the option-parsing loop `for (i=1; i<argc-3; i++)` only executes
#    when argc >= 5, and argc >= 5 ALWAYS falls through to PerformActions()
#    (serial port open). So genuine per-option parsing is NOT observable
#    without hardware.
#  - SOFTWARE path: when argc < 5, ReadArguments() skips the parse loop, prints
#    the version banner + full usage text and calls exit(1), WITHOUT opening
#    any serial port or touching hardware. This is the ONLY verifiable,
#    hardware-independent CLI contract, and it is what we test here.
set -u

LPC="${LPC21ISP:-lpc21isp}"

echo "[test] lpc21isp present and executable (CLI starts)"
command -v "$LPC" >/dev/null 2>&1 || { echo "FAIL: $LPC not found in PATH"; exit 1; }
echo "OK: $LPC found in PATH"

echo "[test] lpc21isp is an AArch64 ELF for musl (cross-compile target OK)"
# Hardware-free confirmation of the build target (OHOS AArch64 musl).
# Resolve the absolute path: `file` does not search PATH.
LPC_PATH=$(command -v "$LPC")
FILE_OUT=$(file "$LPC_PATH" 2>/dev/null)
echo "$FILE_OUT"
echo "$FILE_OUT" | grep -q "arm64" || { echo "FAIL: binary is not AArch64"; exit 1; }
echo "$FILE_OUT" | grep -q "ld-musl-aarch64" || { echo "FAIL: not dynamically linked to musl"; exit 1; }
echo "OK: AArch64 ELF, dynamic musl linker"

echo "[test] lpc21isp <no-args> prints version banner and usage, exits 1"
OUT=$("$LPC" 2>&1); CODE=$?
echo "$OUT"
if [ "$CODE" -ne 1 ]; then
    echo "FAIL: expected exit code 1, got $CODE"
    exit 1
fi
echo "$OUT" | grep -q "Version 1.97 compiled for" || { echo "FAIL: version banner not found"; exit 1; }
echo "$OUT" | grep -q "Portable command line ISP" || { echo "FAIL: banner title not found"; exit 1; }
echo "OK: version banner present, exit code 1"

echo "[test] lpc21isp prints usage syntax and documented option list"
# The usage text is the CLI's contract; verify the documented options are real.
echo "$OUT" | grep -q "Syntax:.*lpc21isp.*comport baudrate Oscillator_in_kHz" || { echo "FAIL: syntax line not found"; exit 1; }
echo "$OUT" | grep -q -- "-hex" || { echo "FAIL: -hex option not documented"; exit 1; }
echo "$OUT" | grep -q -- "-bin" || { echo "FAIL: -bin option not documented"; exit 1; }
echo "$OUT" | grep -q -- "-detectonly" || { echo "FAIL: -detectonly option not documented"; exit 1; }
echo "$OUT" | grep -q -- "-NXPARM" || { echo "FAIL: -NXPARM option not documented"; exit 1; }
echo "$OUT" | grep -q -- "-ADARM" || { echo "FAIL: -ADARM option not documented"; exit 1; }
echo "$OUT" | grep -q -- "-verify" || { echo "FAIL: -verify option not documented"; exit 1; }
echo "OK: usage syntax and option list present"

echo "[test] lpc21isp version banner is stable across invocations (deterministic)"
OUT2=$("$LPC" 2>&1); CODE2=$?
if [ "$CODE2" -ne 1 ]; then
    echo "FAIL: expected exit code 1, got $CODE2"
    exit 1
fi
# The version + copyright header must be byte-identical between runs.
HDR1=$(printf '%s' "$OUT" | sed -n '/^Portable command line ISP$/,/^$/p')
HDR2=$(printf '%s' "$OUT2" | sed -n '/^Portable command line ISP$/,/^$/p')
if [ "$HDR1" != "$HDR2" ]; then
    echo "FAIL: banner header differs between runs"
    exit 1
fi
echo "OK: banner header deterministic across runs"

echo
echo "=== ALL TESTS PASSED ==="
