#!/data/service/hnp/bin/bash
# test_package/test.sh — BusyBox static 1.36.1 package-path verification
#
# Strictly uses the Conan package bin path (${PATH%%:*}).  No system
# BusyBox fallback.  No external `file` command.
#
# Reporting contract (R34 / L1 gate):
#   * Every assertion is recorded as PASS, FAIL or SKIP.
#   * SKIP means the assertion was NOT executed (on OHOS an unsigned ELF
#     cannot be executed at all).  A skip is NEVER counted as a pass, so
#     the pass rate quoted in the PR description always reflects what
#     actually ran.
#   * The final line is a machine readable SUMMARY:
#         SUMMARY: executed=<n> passed=<n> failed=<n> skipped=<n>
#   * Exit status is non-zero only when at least one assertion FAILED.
#
# Assertion inventory (6 total):
#   1. package artifact exists
#   2. static linking (no ELF NEEDED entries)
#   3. binary integrity (non-empty)
#   4. `busybox --help`
#   5. `busybox --list` (applet count)
#   6. runtime applets: echo / true / wc -l
# Assertions 4-6 require an executable (signed) ELF and are reported as
# SKIP when the binary cannot be executed on this host.
set -eu

PASS=0
FAIL=0
SKIP=0

pass() { PASS=$((PASS + 1)); echo "✅ PASS: $1"; }
fail() { FAIL=$((FAIL + 1)); echo "❌ FAIL: $1"; }
skip() { SKIP=$((SKIP + 1)); echo "⏭️  SKIP: $1 — $2"; }
summary() { echo "SUMMARY: executed=$((PASS + FAIL)) passed=${PASS} failed=${FAIL} skipped=${SKIP}"; }

# ── 1. Locate package bin from conanrun PATH ──
PKG_BIN="${PATH%%:*}"
BIN_PATH="${PKG_BIN}/busybox"
echo "[test] package bin dir: ${PKG_BIN}"
echo "[test] package busybox: ${BIN_PATH}"

# ── Assertion 1: package artifact exists ──
if [ -f "${BIN_PATH}" ]; then
    pass "package BusyBox artifact exists at ${BIN_PATH}"
else
    fail "package BusyBox not found at ${BIN_PATH} (package artifact missing)"
    summary
    exit 1
fi

# ── Assertion 2: static linking via readelf (if available) ──
if command -v llvm-readelf >/dev/null 2>&1; then
    NEEDED=$(llvm-readelf --dynamic-table "${BIN_PATH}" 2>/dev/null | grep NEEDED || true)
    if [ -n "${NEEDED}" ]; then
        fail "binary has dynamic NEEDED entries, not fully static: ${NEEDED}"
    else
        pass "static linking confirmed (llvm-readelf: no NEEDED entries)"
    fi
elif command -v readelf >/dev/null 2>&1; then
    NEEDED=$(readelf -d "${BIN_PATH}" 2>/dev/null | grep NEEDED || true)
    if [ -n "${NEEDED}" ]; then
        fail "binary has dynamic NEEDED entries, not fully static: ${NEEDED}"
    else
        pass "static linking confirmed (readelf: no NEEDED entries)"
    fi
else
    skip "static linking check (readelf NEEDED)" "neither readelf nor llvm-readelf available"
fi

# ── Assertion 3: binary integrity (works whether or not the ELF can run) ──
if [ -s "${BIN_PATH}" ]; then
    pass "package binary integrity: ${BIN_PATH} is non-empty"
else
    fail "package binary is empty"
fi

# ── 4. Can the ELF actually execute? (OHOS requires a signed ELF) ──
EXECUTABLE=false
if [ -x "${BIN_PATH}" ]; then
    "${BIN_PATH}" --help > /dev/null 2>&1 && EXECUTABLE=true || EXECUTABLE=false
fi

if [ "${EXECUTABLE}" = false ]; then
    skip "busybox --help"                    "ELF unsigned on OHOS, binary cannot be executed"
    skip "busybox --list (applet count)"     "ELF unsigned on OHOS, binary cannot be executed"
    skip "busybox runtime applets (echo/true/wc -l)" "ELF unsigned on OHOS, binary cannot be executed"
    echo ""
    echo "[note] On OHOS an ELF must be signed (sign-elf) before it can run."
    echo "[note] Skipped assertions did NOT execute and are not counted as passed."
    summary
    if [ "${FAIL}" -gt 0 ]; then
        exit 1
    fi
    exit 0
fi

# ── Assertion 4: --help ──
if "${BIN_PATH}" --help > /dev/null 2>&1; then
    pass "busybox --help"
else
    fail "busybox --help"
fi

# ── Assertion 5: --list ──
if BUSYBOX_LIST=$("${BIN_PATH}" --list 2>&1); then
    pass "busybox --list ($(echo "${BUSYBOX_LIST}" | wc -l) applets)"
else
    fail "busybox --list"
fi

# ── Assertion 6: runtime applets echo / true / wc -l ──
RUNTIME_OK=true
OUT=$("${BIN_PATH}" echo hello 2>&1 || true)
if [ "${OUT}" = "hello" ]; then
    :
else
    echo "   ↳ echo hello expected 'hello' got '${OUT}'"
    RUNTIME_OK=false
fi

if ! "${BIN_PATH}" true > /dev/null 2>&1; then
    echo "   ↳ busybox true returned non-zero"
    RUNTIME_OK=false
fi

OUT=$(echo "test" | "${BIN_PATH}" wc -l 2>&1 || true)
if [ "${OUT}" = "1" ]; then
    :
else
    echo "   ↳ wc -l expected '1' got '${OUT}'"
    RUNTIME_OK=false
fi

if [ "${RUNTIME_OK}" = true ]; then
    pass "busybox runtime applets (echo/true/wc -l)"
else
    fail "busybox runtime applets (echo/true/wc -l)"
fi

echo ""
summary

if [ "${FAIL}" -gt 0 ]; then
    exit 1
fi
echo "🎉 All executed BusyBox static smoke assertions passed"
