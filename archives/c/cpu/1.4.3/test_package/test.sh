#!/usr/bin/env bash
#
# test.sh -- Conan L1 tests for cpu 1.4.3 (HarmonyOS PC / OHOS aarch64).
#
# Started by test_package/conanfile.py inside the `conanrun' environment:
#   PATH             the package bindirs (sbin, bin)
#   LD_LIBRARY_PATH  the package and dependency lib dirs
#   CPU_TEST_ROOT    the package folder under test
#
# Upstream 1.4.3 has no test suite (the top-level `check' target has no TESTS
# entries and doc/test.ldif is LDAP fixture data), so the cases below are the
# adaptation tests.  Every assertion is deliberate about what it proves, and
# the unknown-method case is a negative control for the plugin-loading check.
set -u

ROOT="${CPU_TEST_ROOT:?CPU_TEST_ROOT is not set}"
CPU="${ROOT}/bin/cpu"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/cpu-test-XXXXXX")"
PASS=0
FAIL=0

ok()  { PASS=$((PASS + 1)); printf 'PASS  %s\n' "$1"; }
bad() { FAIL=$((FAIL + 1)); printf 'FAIL  %s\n' "$1"; }

# cpu reports failures on stdout/stderr but exits 0, so every check inspects the
# captured output instead of the exit status.
run() { timeout 60 "$@" >"$WORK/out" 2>&1 || true; }

contains()
{
    if grep -qF -- "$2" "$WORK/out"; then
        ok "$1"
    else
        bad "$1"
        printf '      expected to find: %s\n      --- output ---\n' "$2"
        sed 's/^/      /' "$WORK/out"
    fi
}

absent()
{
    if grep -qF -- "$2" "$WORK/out"; then
        bad "$1"
        printf '      not expected: %s\n      --- output ---\n' "$2"
        sed 's/^/      /' "$WORK/out"
    else
        ok "$1"
    fi
}

trap 'rm -rf "$WORK"' EXIT
printf '== cpu 1.4.3 package tests ==\n'

# --- 1. package contents ---------------------------------------------------
for f in bin/cpu lib/libcputil.so lib/libcpu_ldap.so; do
    if [ -e "${ROOT}/${f}" ]; then ok "package ships ${f}"; else bad "package ships ${f}"; fi
done

# --- 2. CLI contract ------------------------------------------------------
run "${CPU}" --version
contains "--version reports the upstream version 1.4.3" "1.4.3"
run "${CPU}" --help
contains "--help prints the usage line" "USAGE: cpu"
contains "--help documents the method option" "--method="

# --- 3. method plugin loading --------------------------------------------
# Negative control: an unknown method must fail inside the loader, which proves
# that the following check is able to fail.
printf 'LDAP_URI = ldap://127.0.0.1:1\nLDAP_BASE = dc=example,dc=com\n' > "${WORK}/cpu.conf"
run "${CPU}" -M bogus -C "${WORK}/cpu.conf" -y cat root
contains "unknown method fails in CPU_loadLibrary (negative control)" "CPU_loadLibrary"

# The ldap method plugin has to dlopen() and take over from the loader.  The
# closed port keeps the exchange offline and deterministic; the assertions are
# about the loader giving way to the plugin, not about a reachable server.
printf 'LDAP_URI = ldap://127.0.0.1:1\nLDAP_BASE = dc=example,dc=com\n' > "${WORK}/cpu.conf"
run "${CPU}" -M ldap -C "${WORK}/cpu.conf" -y cat root
absent "ldap plugin loads (no CPU_loadLibrary failure)" "CPU_loadLibrary"
absent "ldap plugin loads (no 'error loading the ldap library')" "loading the ldap library"

# --- 4. consumer test ------------------------------------------------------
# consumer.c links the package's libcputil.so and drives its public helpers.
# The toolchain clang driver spawns lld, which is dynamically linked against
# libxml2.so.16 from the SDK's llvm/lib; conanrun exports the package dirs only,
# so put the toolchain lib dir on the loader path explicitly.  Without it the
# link step depends on whatever the invoking shell exports and fails on a clean
# worker with:
#   Error loading shared library libxml2.so.16: (needed by .../llvm/bin/lld)
CC="${CC:-clang}"
cc_bin="$(command -v "${CC}" 2>/dev/null || true)"
[ -n "${cc_bin}" ] || cc_bin="${CC}"
cc_real="$(readlink -f "${cc_bin}" 2>/dev/null || echo "${cc_bin}")"
cc_lib="$(cd "$(dirname "${cc_real}")/../lib" 2>/dev/null && pwd || true)"
if [ -n "${cc_lib}" ] && [ -e "${cc_lib}/libxml2.so.16" ]; then
    LD_LIBRARY_PATH="${cc_lib}${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}"
    export LD_LIBRARY_PATH
fi
linked=no
"${CC}" -o "${WORK}/consumer" "$(dirname "$0")/consumer.c" \
        -L"${ROOT}/lib" -lcputil >"${WORK}/cc.log" 2>&1 && linked=yes
if [ "${linked}" = no ] && grep -q 'libxml2' "${WORK}/cc.log"; then
    # Last resort: lld itself cannot start (no libxml2 on the loader path);
    # GNU ld from the same toolchain has no such dependency.  Keep the first
    # log for the failure report.
    echo "--- retry with -fuse-ld=bfd ---" >>"${WORK}/cc.log"
    "${CC}" -fuse-ld=bfd -o "${WORK}/consumer" "$(dirname "$0")/consumer.c" \
            -L"${ROOT}/lib" -lcputil >>"${WORK}/cc.log" 2>&1 && linked=yes
fi
if [ "${linked}" = yes ]; then
    # HMDFS: the linker does not always leave the exec bit on the output.
    chmod +x "${WORK}/consumer" 2>/dev/null || true
    ok "consumer.c compiles and links against libcputil.so"
    if "${WORK}/consumer" "${WORK}" >"${WORK}/consumer.out" 2>&1; then
        ok "consumer test passes"
    else
        bad "consumer test passes"
    fi
    sed 's/^/      /' "${WORK}/consumer.out"
else
    bad "consumer.c compiles and links against libcputil.so"
    sed 's/^/      /' "${WORK}/cc.log"
fi

printf '== %d passed, %d failed ==\n' "${PASS}" "${FAIL}"
[ "${FAIL}" -eq 0 ]
