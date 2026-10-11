#!/data/service/hnp/bin/bash
# test_package/test.sh — HarmonyOS verification for the qrq OHAudio port.
#
# 1. Smoke test: the shipped binary must run and report its version.
# 2. HarmonyOS-specific: the binary must be linked against the native
#    OHAudio backend (only the OHOS port links libohaudio).
#
# Note: grep is used without -q so it consumes the whole stream; `grep -q`
# closes the pipe early and would make readelf die with SIGPIPE, which
# `set -o pipefail` would then report as a failure.
set -euo pipefail

qrq_bin="$(command -v qrq)"
echo "[test] qrq binary: ${qrq_bin}"
[ -n "${qrq_bin}" ] || { echo "[test] FAIL: qrq not found in PATH" >&2; exit 1; }

help_out="$(qrq -h 2>&1)"
case "${help_out}" in
    *"qrq v0.3.5"*)
        echo "[test] PASS: 'qrq -h' reports v0.3.5"
        ;;
    *)
        echo "[test] FAIL: unexpected 'qrq -h' output:" >&2
        printf '%s\n' "${help_out}" >&2
        exit 1
        ;;
esac

if readelf -d "${qrq_bin}" 2>/dev/null | grep "libohaudio" >/dev/null; then
    echo "[test] PASS: qrq links libohaudio (native OHAudio backend active)"
else
    echo "[test] FAIL: qrq is not linked against libohaudio" >&2
    exit 1
fi
