#!/usr/bin/env bash
# End-to-end test driver for paml 4.10.10 (L0c test source file).
#
# Executes the packaged OHOS aarch64 target binaries (not host binaries)
# and asserts values taken from the upstream reference output
# (examples/YN00abglobin.result.txt). Upstream ships no test suite, so
# these assertions are the package's functional coverage:
#
#   Test 1  chi2 : feed 'q' to quit after the first table, assert the
#                  chi-square critical value for DF=1, p=0.05 (3.8415).
#   Test 2  yn00 : ML pairwise dN/dS run on the upstream abglobin.nuc
#                  sample (5 sequences x 285 codons); compare the
#                  NG86 / YN2000 / LWL85 estimates against upstream
#                  reference values.
#   Test 3       : all 10 CLI binaries present and executable.
#   Test 4       : OHOS platform-specific — each of the 10 binaries is a
#                  native OHOS aarch64 ELF executable (ELF magic +
#                  ELFCLASS64 + e_machine EM_AARCH64, byte-level via od,
#                  no readelf dependency) and, when readelf is available,
#                  its dynamic NEEDED entries are only system libs
#                  (libc.so/libm.so) — no host libs, no conan leakage.
#
# Usage: run_tests.sh <package bin dir>
# Exit code: 0 when every assertion passes, 1 otherwise.

set -u

BIN_DIR="${1:-}"
if [ -z "$BIN_DIR" ]; then
    echo "usage: run_tests.sh <package bin dir>" >&2
    exit 2
fi

PASS=0
FAIL=0

# A real assertion: counted toward the pass/fail total.
check() {
    local label="$1"
    shift
    if "$@"; then
        PASS=$((PASS + 1))
        echo "  [ok]   $label"
    else
        FAIL=$((FAIL + 1))
        echo "  [fail] $label" >&2
    fi
}

# A run step (produces output files asserted on later): fatal on error
# but not counted as an assertion itself.
run_step() {
    local label="$1"
    shift
    if "$@"; then
        echo "  [run]  $label"
    else
        echo "  [fail] $label (run step)" >&2
        exit 1
    fi
}

# --- Test 1: chi2 — chi-square critical value table ---
chi2="$BIN_DIR/chi2"
run_step "chi2: runs (stdin 'q' quits after first table)" \
    bash -c "printf 'q\n' | '$chi2' > chi2.out"
# Substantive assertion: DF=1 critical value at p=0.05 is 3.8415
check "chi2: DF=1 p=0.05 critical value 3.8415" \
    grep -q '3.8415' chi2.out

# --- Test 2: yn00 — ML pairwise dN/dS on upstream abglobin sample ---
# Sample data (abglobin.nuc) + control file (yn00.ctl, outfile rewritten
# to yn.result) live next to this script in the test_package folder.
yn00="$BIN_DIR/yn00"
run_step "yn00: ML run on abglobin.nuc" \
    bash -c "'$yn00' yn00.ctl > yn00.stdout"
check "yn00: dataset size ns = 5" \
    grep -Eq 'ns =   5' yn.result
check "yn00: codon length ls = 285" \
    grep -Eq 'ls = 285' yn.result
# Nei-Gojobori 1986, human vs goat-cow: omega 0.251 (0.0863 0.3443)
check "yn00: NG86 dN/dS 1v2" \
    grep -Eq '0\.2507 \(0\.0863 0\.3443\)' yn.result
# Yang & Nielsen 2000, pair 2v1: S=183.7 N=671.3 kappa=1.5804
check "yn00: YN2000 S 2v1" \
    grep -Eq '183\.7' yn.result
check "yn00: YN2000 kappa" \
    grep -Eq '1\.5804' yn.result
# LWL85, human vs goat-cow (upstream reference line, exact)
check "yn00: LWL85 1v2" \
    grep -Eq 'LWL85:  dS =  0\.3495 dN =  0\.0856 w = 0\.2450 S =  212\.2 N =  642\.8' yn.result

# --- Test 3: all 10 binaries present and executable ---
for tool in baseml basemlg codeml evolver pamp yn00 mcmctree infinitesites chi2 ds; do
    check "binary: $tool is executable" test -x "$BIN_DIR/$tool"
done

# --- Test 4: OHOS platform-specific — native aarch64 ELF, system libs only ---
# Byte-level ELF header check (works without readelf, od is POSIX):
#   byte 0-3  = 7f 45 4c 46 (ELF magic)
#   byte 4    = 02          (ELFCLASS64)
#   byte 18-19 = b7 00 LE   (e_machine = 0x00b7 = EM_AARCH64)
is_ohos_aarch64_elf() {
    od -An -tx1 -j0 -N4 "$1" | grep -q '7f 45 4c 46' \
        && od -An -tx1 -j4 -N1 "$1" | grep -q '02' \
        && od -An -tx1 -j18 -N2 "$1" | grep -q 'b7 00'
}

# One assertion per binary: native aarch64 ELF (byte-level, always) AND,
# when readelf is available, no NEEDED entry outside system libs
# (no host libs, no conan dependency leakage).
ohos_binary_ok() {
    is_ohos_aarch64_elf "$1" || return 1
    if command -v readelf >/dev/null 2>&1; then
        readelf -d "$1" 2>/dev/null | grep -E 'NEEDED' \
            | grep -qEv 'libc\.so|libm\.so' && return 1
    fi
    return 0
}

for tool in baseml basemlg codeml evolver pamp yn00 mcmctree infinitesites chi2 ds; do
    check "ohos: $tool is native OHOS aarch64 ELF, system libs only" \
        ohos_binary_ok "$BIN_DIR/$tool"
done

echo ""
echo "run_tests.sh: $PASS assertions passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
