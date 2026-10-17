#!/bin/bash
# test.sh — avida 2.12.4 consumer test for OHOS
# Validates that the packaged avida binary executes, completes a minimal
# simulation run, and is an AArch64 ELF (OHOS armv8 hard requirement).

set -euo pipefail

AVIDA_BIN=""
CONSUMER_CASE_DIR=""
WORK_DIR=""

# The simulation work directory is removed on every exit path, including the
# early "exit 1" of a failing assertion, so no temporary state is left behind.
# Failures here are swallowed on purpose: not being able to delete a temp dir
# must never overwrite the exit status the assertions produced.
cleanup() {
    if [[ -n "${WORK_DIR}" && -d "${WORK_DIR}" ]]; then
        rm -rf "${WORK_DIR}" 2>/dev/null || true
    fi
}
trap cleanup EXIT

# Locate the avida binary
# 1. Try PATH first (if VirtualRunEnv adds bindirs)
if command -v avida >/dev/null 2>&1; then
    AVIDA_BIN="$(command -v avida)"
# 2. Fall back to AVIDA_PACKAGE_DIR/work/avida
elif [[ -n "${AVIDA_PACKAGE_DIR:-}" && -x "${AVIDA_PACKAGE_DIR}/work/avida" ]]; then
    AVIDA_BIN="${AVIDA_PACKAGE_DIR}/work/avida"
# 3. Last resort — search common locations
else
    for candidate in \
        "${AVIDA_PACKAGE_DIR:-}/work/avida" \
        "${AVIDA_PACKAGE_DIR:-}/bin/avida"; do
        if [[ -x "${candidate}" ]]; then
            AVIDA_BIN="${candidate}"
            break
        fi
    done
fi

if [[ -z "${AVIDA_BIN}" ]]; then
    echo "FAIL: avida binary not found on PATH or in package dir"
    exit 1
fi

echo "Using avida binary: ${AVIDA_BIN}"

# Locate consumer-case directory (for config files)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -d "${SCRIPT_DIR}/consumer-case" ]]; then
    CONSUMER_CASE_DIR="${SCRIPT_DIR}/consumer-case"
fi

# Test 1: binary executes
echo "=== Test 1: avida binary execution ==="
if "${AVIDA_BIN}" --version >/dev/null 2>&1; then
    echo "PASS: avida --version executed"
elif "${AVIDA_BIN}" --help >/dev/null 2>&1; then
    echo "PASS: avida --help executed"
else
    echo "FAIL: neither --version nor --help succeeded"
    exit 1
fi

# Test 2: run minimal avida simulation with consumer-case configs
echo "=== Test 2: minimal avida run ==="
WORK_DIR="$(mktemp -d)"

# Use consumer-case configs if available, otherwise use inline minimal config
if [[ -n "${CONSUMER_CASE_DIR}" ]]; then
    cp "${CONSUMER_CASE_DIR}/avida.cfg" "${WORK_DIR}/avida.cfg"
    # Copy optional environment/events configs if they have content
    if [[ -s "${CONSUMER_CASE_DIR}/environment.cfg" ]]; then
        cp "${CONSUMER_CASE_DIR}/environment.cfg" "${WORK_DIR}/environment.cfg"
    fi
    if [[ -s "${CONSUMER_CASE_DIR}/events.cfg" ]]; then
        cp "${CONSUMER_CASE_DIR}/events.cfg" "${WORK_DIR}/events.cfg"
    fi
    echo "Using consumer-case configs from ${CONSUMER_CASE_DIR}"
else
    cat > "${WORK_DIR}/avida.cfg" <<'CFGEOF'
WORLD-X 10
WORLD-Y 10
SLICING-MAX 100
END-UP 10
RANDOM-SEED 42
CFGEOF
    echo "Using inline minimal config"
fi

# The simulation is captured to a file so that its own exit status is observed.
# Testing the command directly (rather than through a pipe) is required: under
# `set -e` a failure would otherwise abort the script before the status is read,
# and piping into head would report head's status instead of avida's.
cd "${WORK_DIR}"
if "${AVIDA_BIN}" -v 1 > "${WORK_DIR}/avida.log" 2>&1; then
    RC=0
else
    RC=$?
fi

echo "--- first 20 lines of simulation output ---"
head -20 "${WORK_DIR}/avida.log"
echo "--- end of simulation output ---"

if [[ "${RC}" -ne 0 ]]; then
    echo "FAIL: avida simulation exited with code ${RC}"
    exit 1
fi
echo "PASS: avida simulation completed (exit code: ${RC})"

# Test 3: OHOS-specific — the packaged binary must be an AArch64 ELF.
# The ELF header is read byte by byte with od(1) and compared against the
# AArch64 machine id (e_machine == 0xB7). Matching on the human-readable output
# of file(1) is not reliable because that string differs between
# implementations ("aarch64", "ARM aarch64", "arm64", ...), so it is only used
# when od(1) itself is unavailable.
echo "=== Test 3: AArch64 ELF check ==="
if ! command -v od >/dev/null 2>&1; then
    FILE_OUT="$(file "${AVIDA_BIN}" 2>/dev/null || echo "")"
    if [[ "${FILE_OUT}" =~ (aarch64|arm64) ]]; then
        echo "PASS: packaged binary reported as arm64 by file(1): ${FILE_OUT}"
    else
        echo "FAIL: od(1) unavailable and file(1) did not report aarch64/arm64: ${FILE_OUT}"
        exit 1
    fi
else
    ELF_MAGIC="$(od -An -v -tx1 -N4 "${AVIDA_BIN}" 2>/dev/null | tr -d ' \n' || true)"
    ELF_MACHINE="$(od -An -v -tx1 -j18 -N2 "${AVIDA_BIN}" 2>/dev/null | tr -d ' \n' || true)"

    if [[ "${ELF_MAGIC}" != "7f454c46" ]]; then
        echo "FAIL: packaged binary is not an ELF file (magic=${ELF_MAGIC})"
        exit 1
    fi

    # e_machine is a 16-bit field at offset 18; 0x00B7 identifies AArch64.
    # Both byte orders are accepted because the field encoding follows the ELF
    # data encoding, so a big-endian AArch64 object would read "00b7".
    case "${ELF_MACHINE}" in
        b700|00b7)
            echo "PASS: packaged binary is an AArch64 ELF (e_machine=0xB7)"
            ;;
        *)
            echo "FAIL: unexpected ELF e_machine bytes '${ELF_MACHINE}' (AArch64 requires b700/00b7)"
            exit 1
            ;;
    esac
fi

echo ""
echo "ALL TESTS PASSED"
exit 0
