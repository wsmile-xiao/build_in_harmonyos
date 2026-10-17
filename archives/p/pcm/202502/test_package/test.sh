#!/usr/bin/env bash
# Real-execution test suite for the packaged Intel(R) PCM 202502 command line
# tools on HarmonyOS PC (OHOS aarch64).
#
# Every assertion below runs a packaged artifact and checks its real output or
# its real ELF identity.  `set -e` is deliberately NOT used: several upstream
# tools exit with EXIT_FAILURE after printing their help text, and this suite
# has to observe those exit codes instead of aborting on them.  `set -u` and
# `set -o pipefail` are kept.

set -uo pipefail

PKG="${PCM_PKG_FOLDER:?PCM_PKG_FOLDER must point at the packaged pcm folder}"
BIN="${PKG}/bin"
SHARE="${PKG}/share"

PASS=0
FAIL=0

# ---------------------------------------------------------------------------
# Local execution shims.
#
# The delivered binaries are linked against the real HarmonyOS libc, which
# exports the __*_chk fortify helpers plus backtrace()/backtrace_symbols() that
# upstream's src/utils.cpp uses.  When an x86 build host has to execute those
# aarch64 images through a musl guest runtime, that runtime can be an older libc
# without the fortify helpers, and the loader then aborts with exit 127 before
# main() is reached.  That is a property of the local execution environment, not
# of the package: a native OHOS CI worker runs the very same binaries against the
# real libc and needs no preload at all.
#
# So the shims are injected only when the files exist, and only into the aarch64
# process being launched -- never exported into the environment of the whole
# script, which would make every x86 helper process try to preload an aarch64
# object.  The shims are forwarding stubs: they call the real memset()/memcpy()/
# send() and report "no unwinder available" for backtrace(), exactly like a libc
# built without stack unwinding.  They are not part of the recipe and are not
# shipped in the package.
# ---------------------------------------------------------------------------
SHIM_DIR="${PCM_TEST_SHIM_DIR:-/opt/ohos-guest/lib}"
SHIMS=""
for _shim in \
    "${SHIM_DIR}/libchkfcnshim.so" \
    "${SHIM_DIR}/libpcmchkshim.so" \
    /root/xc-shims/libchkfcnshim.so \
    /root/xc-shims/libpcmchkshim.so
do
    if [ -f "${_shim}" ]; then
        SHIMS="${SHIMS:+${SHIMS}:}${_shim}"
    fi
done

run_tool() {
    if [ -n "${SHIMS}" ]; then
        LD_PRELOAD="${SHIMS}" "$@"
    else
        "$@"
    fi
}

ok() {
    PASS=$((PASS + 1))
    echo "PASS [$1] $2"
}

ko() {
    FAIL=$((FAIL + 1))
    echo "FAIL [$1] $2"
}

check_contains() {
    # check_contains <id> <description> <needle> <file>
    if grep -qF -- "$3" "$4" 2>/dev/null; then
        ok "$1" "$2"
    else
        ko "$1" "$2 (missing '$3')"
        echo "----- actual output of $4 -----"
        head -c 1200 "$4"
        echo
        echo "-----"
    fi
}

check_absent() {
    # check_absent <id> <description> <needle> <file>
    if grep -qF -- "$3" "$4" 2>/dev/null; then
        ko "$1" "$2 (unexpected '$3')"
        echo "----- actual output of $4 -----"
        head -c 1200 "$4"
        echo
        echo "-----"
    else
        ok "$1" "$2"
    fi
}

check_rc_zero() {
    # check_rc_zero <id> <description> <actual rc>
    if [ "$3" -eq 0 ]; then
        ok "$1" "$2"
    else
        ko "$1" "$2 (exit code $3)"
    fi
}

dump_on_fail() {
    # dump_on_fail <file>
    echo "----- actual output of $1 -----"
    head -c 1200 "$1"
    echo
    echo "-----"
}

OUT="$(mktemp -d)"
trap 'rm -rf "$OUT"' EXIT

# ---------------------------------------------------------------------------
# 1. Upstream version identity.  --version is handled before the PCM object is
#    constructed, so it exercises the packaged binary without any PMU access.
# ---------------------------------------------------------------------------
run_tool "${BIN}/pcm" --version >"${OUT}/version.txt" 2>&1
rc=$?
check_rc_zero 1 "pcm --version exits 0" "$rc"
check_contains 2 "pcm --version reports the upstream 202502 build id" \
    "ID=5cb70ffd" "${OUT}/version.txt"

# ---------------------------------------------------------------------------
# 2. Help output of three independent tools.  Upstream calls exit(EXIT_FAILURE)
#    after print_help(), so the exit code is not asserted here.
# ---------------------------------------------------------------------------
run_tool "${BIN}/pcm" --help >"${OUT}/pcm-help.txt" 2>&1
check_contains 3 "pcm --help prints its usage block" "Usage:" "${OUT}/pcm-help.txt"
run_tool "${BIN}/pcm-memory" --help >"${OUT}/memory-help.txt" 2>&1
check_contains 4 "pcm-memory --help prints its usage block" "Usage:" "${OUT}/memory-help.txt"
run_tool "${BIN}/pcm-power" --help >"${OUT}/power-help.txt" 2>&1
check_contains 5 "pcm-power --help prints its usage block" "Usage:" "${OUT}/power-help.txt"

# ---------------------------------------------------------------------------
# 3. pcm-raw is the tool that parses the Intel perfmon event JSON through
#    simdjson.  It must be the simdjson-enabled variant, not the "compiled
#    without simdjson library" fallback the upstream CMake emits when the
#    dependency is missing.
# ---------------------------------------------------------------------------
run_tool "${BIN}/pcm-raw" --help >"${OUT}/raw-help.txt" 2>&1
check_absent 6 "pcm-raw is not the no-simdjson fallback build" \
    "compiled without simdjson library" "${OUT}/raw-help.txt"

# ---------------------------------------------------------------------------
# 4. HarmonyOS specific: patch 0001 keeps the CPUID instruction on x86 only and
#    reports the reserved zero leaf on aarch64.  Running the tool with no
#    arguments therefore has to say the CPU is unsupported -- it must never
#    print an invented Intel CPU identity or a fabricated uarch codename.
# ---------------------------------------------------------------------------
run_tool "${BIN}/pcm" >"${OUT}/pcm-run.txt" 2>&1
check_contains 7 "pcm reports the non-Intel CPU honestly instead of fabricating CPUID data" \
    "Error: unsupported processor. Only Intel(R) processors are supported" "${OUT}/pcm-run.txt"
check_contains 8 "pcm reports the real outcome of its PMU access attempt" \
    "no MSR or PCI CFG space access" "${OUT}/pcm-run.txt"

# ---------------------------------------------------------------------------
# 5. The same for a second, independently compiled tool: pcm-power must reach
#    the uarch dispatch and report the model it really read.
# ---------------------------------------------------------------------------
run_tool "${BIN}/pcm-power" >"${OUT}/power-run.txt" 2>&1
check_contains 9 "pcm-power reaches PMU init and reports the real processor model" \
    "Unsupported processor model" "${OUT}/power-run.txt"

# ---------------------------------------------------------------------------
# 6. The packaged tools must be AArch64 ELF images, and no host x86_64 leftover
#    may ship next to them.
# ---------------------------------------------------------------------------
if readelf -h "${BIN}/pcm" 2>/dev/null | grep -q "Machine:.*AArch64"; then
    ok 10 "packaged pcm is an AArch64 ELF image"
else
    ko 10 "packaged pcm is an AArch64 ELF image"
    readelf -h "${BIN}/pcm" 2>&1 | head -20
fi

foreign=""
for f in "${BIN}"/*; do
    [ -f "$f" ] || continue
    head -c 4 "$f" | grep -q "ELF" || continue
    if ! readelf -h "$f" 2>/dev/null | grep -q "Machine:.*AArch64"; then
        foreign="${foreign} $(basename "$f")"
    fi
done
if [ -z "${foreign}" ]; then
    ok 11 "all packaged ELF tools are AArch64"
else
    ko 11 "all packaged ELF tools are AArch64 (not AArch64:${foreign})"
fi

# ---------------------------------------------------------------------------
# 7. The complete upstream tool set is delivered, daemon and client included.
# ---------------------------------------------------------------------------
missing=""
for t in pcm pcm-accel pcm-core pcm-iio pcm-latency pcm-lspci pcm-memory \
         pcm-mmio pcm-msr pcm-numa pcm-pcie pcm-pcicfg pcm-power pcm-raw \
         pcm-sensor pcm-sensor-server pcm-tpmi pcm-tsx pcm-daemon pcm-client; do
    [ -e "${BIN}/${t}" ] || missing="${missing} ${t}"
done
if [ -z "${missing}" ]; then
    ok 12 "all 20 upstream command line tools are packaged"
else
    ko 12 "all 20 upstream command line tools are packaged (missing:${missing})"
fi

# ---------------------------------------------------------------------------
# 8. The pcm-client half of the daemon/client pair really runs and reports its
#    own usage instead of failing to load.
# ---------------------------------------------------------------------------
run_tool "${BIN}/pcm-client" >"${OUT}/client.txt" 2>&1
check_contains 13 "pcm-client runs and prints its usage" "pollMs" "${OUT}/client.txt"

# ---------------------------------------------------------------------------
# 9. The perfmon opcode tables and PMU register declarations that pcm-raw reads
#    at runtime are installed next to the binaries.
# ---------------------------------------------------------------------------
if [ -d "${SHARE}/pcm/PMURegisterDeclarations" ] &&
        ls "${SHARE}"/pcm/opCode-*.txt >/dev/null 2>&1; then
    ok 14 "perfmon opcode tables and PMU register declarations are installed"
else
    ko 14 "perfmon opcode tables and PMU register declarations are installed"
    ls -R "${SHARE}" 2>&1 | head -20
fi

# ---------------------------------------------------------------------------
# 10. The upstream shell helper is installed and executable.
# ---------------------------------------------------------------------------
if [ -x "${BIN}/pcm-bw-histogram" ]; then
    ok 15 "upstream pcm-bw-histogram helper is installed and executable"
else
    ko 15 "upstream pcm-bw-histogram helper is installed and executable"
fi

# ---------------------------------------------------------------------------
# 11. The license and the documentation travel with the package.  Upstream sets
#     CMAKE_INSTALL_DOCDIR from project(PCM), so the directory is share/doc/PCM.
# ---------------------------------------------------------------------------
if [ -f "${SHARE}/licenses/pcm/LICENSE" ] && [ -f "${SHARE}/doc/PCM/README.md" ]; then
    ok 16 "LICENSE and README.md are installed under share/"
else
    ko 16 "LICENSE and README.md are installed under share/"
    ls -R "${SHARE}" 2>&1 | head -20
fi

echo ""
echo "assertions_total=$((PASS + FAIL)) pass=${PASS} fail=${FAIL}"
[ "${FAIL}" -eq 0 ]