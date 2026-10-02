#!/bin/sh
# test_package/test.sh — artifact and script-level checks for pconsole 1.2.0.
#
# pconsole ships three files in bin/: the pconsole ELF plus the pconsole.sh
# driver script and the ssh.sh wrapper.  The behavioural surface of the two
# scripts is checked here; the ELF itself is exercised by pconsole_pty_test.py
# (it needs a pty, see that file's docstring).
#
# Usage: test.sh <bindir>
set -eu

BINDIR="${1:?usage: test.sh <bindir>}"
FAILED=0
PASSED=0

ok() {
    PASSED=$((PASSED + 1))
    echo "ok: $1"
}

bad() {
    FAILED=$((FAILED + 1))
    echo "FAIL: $1"
}

# ── S1: all three artifacts are installed and executable ──────────────────────
for f in pconsole pconsole.sh ssh.sh; do
    if [ -f "${BINDIR}/${f}" ] && [ -x "${BINDIR}/${f}" ]; then
        ok "S1_installed_${f}"
    else
        bad "S1_installed_${f} (missing or not executable in ${BINDIR})"
    fi
done

# ── S2: the license text is packaged ─────────────────────────────────────────
PKG_DIR=$(dirname "${BINDIR}")
if [ -f "${PKG_DIR}/licenses/GPL" ]; then
    ok "S2_license_packaged"
    if grep -q "GNU GENERAL PUBLIC LICENSE" "${PKG_DIR}/licenses/GPL"; then
        ok "S2b_license_is_gpl_text"
    else
        bad "S2b_license_is_gpl_text"
    fi
else
    bad "S2_license_packaged (no ${PKG_DIR}/licenses/GPL)"
fi

# ── S3: configure baked the *package* bindir into pconsole.sh ────────────────
# configure.in substitutes @prefix@/@bindir@; getting this wrong would ship a
# driver script pointing at /usr/local/bin, so assert the real package path.
# The spelling of the bindir line depends on whether conan's AutotoolsToolchain
# passes an explicit --bindir (it does, because cpp_info.bindirs is non-empty),
# so accept both forms and resolve them against the generated prefix.
SH_PREFIX=$(sed -n 's/^prefix=//p' "${BINDIR}/pconsole.sh" | head -1)
SH_BINDIR=$(sed -n 's/^bindir=//p' "${BINDIR}/pconsole.sh" | head -1)
if [ "${SH_PREFIX}" = "${BINDIR%/*}" ]; then
    ok "S3_pconsole_sh_prefix_is_package_dir"
else
    bad "S3_pconsole_sh_prefix_is_package_dir (got prefix=${SH_PREFIX})"
fi
SH_BINDIR_RESOLVED=$(printf '%s' "${SH_BINDIR}" \
    | sed -e "s|\${prefix}|${SH_PREFIX}|g" -e "s|\${exec_prefix}|${SH_PREFIX}|g")
if [ "${SH_BINDIR_RESOLVED}" = "${BINDIR}" ]; then
    ok "S3b_pconsole_sh_bindir_points_at_package_bin"
else
    bad "S3b_pconsole_sh_bindir_points_at_package_bin (resolved to ${SH_BINDIR_RESOLVED})"
fi

# ── S4: pconsole.sh with no argument prints usage and exits non-zero ─────────
# NOTE: pconsole.sh must NOT be invoked with host arguments.  Without a
# controlling tty its get_tty() loop never terminates and the build times out.
set +e
USAGE_OUT=$(sh "${BINDIR}/pconsole.sh" 2>&1)
USAGE_RC=$?
set -e
if [ "${USAGE_RC}" -ne 0 ]; then
    ok "S4_pconsole_sh_usage_exits_nonzero (rc=${USAGE_RC})"
else
    bad "S4_pconsole_sh_usage_exits_nonzero (rc=0)"
fi
case "${USAGE_OUT}" in
    *"usage: pconsole.sh"*) ok "S4b_pconsole_sh_prints_usage" ;;
    *) bad "S4b_pconsole_sh_prints_usage (got: ${USAGE_OUT})" ;;
esac

# ── S5: both scripts are valid POSIX shell ───────────────────────────────────
for f in pconsole.sh ssh.sh; do
    if sh -n "${BINDIR}/${f}" 2>/dev/null; then
        ok "S5_shell_syntax_${f}"
    else
        bad "S5_shell_syntax_${f}"
    fi
done

# ── S6: ssh.sh really delegates to an external connector ─────────────────────
# ssh.sh overwrites PATH with its own list, so which branch runs depends on the
# host: `type ssh` picks ssh when it is installed, otherwise the telnet
# fallback.  Both branches must be reached and must not succeed silently, so
# assert the dispatcher was reached (non-zero exit plus recognisable output).
SH_ABS=$(command -v sh)
set +e
DISPATCH_OUT=$("${SH_ABS}" "${BINDIR}/ssh.sh" 2>&1)
DISPATCH_RC=$?
set -e
if [ "${DISPATCH_RC}" -ne 0 ] && { [ "${DISPATCH_RC}" -eq 127 ] \
    || printf '%s' "${DISPATCH_OUT}" | grep -qiE 'usage: (ssh|telnet)|not found'; }; then
    ok "S6_ssh_sh_reaches_connector_dispatcher (rc=${DISPATCH_RC})"
else
    bad "S6_ssh_sh_reaches_connector_dispatcher (rc=${DISPATCH_RC} out=${DISPATCH_OUT})"
fi
# Both dispatch forms must be present in the shipped script (structural check:
# the runtime branch cannot be forced from outside, ssh.sh resets PATH itself).
if grep -q 'type ssh' "${BINDIR}/ssh.sh" \
    && grep -q 'telnet' "${BINDIR}/ssh.sh" \
    && grep -q 'ssh \$1 -p \$2' "${BINDIR}/ssh.sh"; then
    ok "S6b_ssh_sh_has_both_dispatch_forms"
else
    bad "S6b_ssh_sh_has_both_dispatch_forms"
fi

echo "PCONSOLE_SH_RESULT={\"executed\": true, \"discovered\": $((PASSED + FAILED)), \"passedCount\": ${PASSED}, \"failed\": ${FAILED}}"
echo "[test] summary: pass=${PASSED} fail=${FAILED} (of $((PASSED + FAILED)))"
[ "${FAILED}" -eq 0 ]
