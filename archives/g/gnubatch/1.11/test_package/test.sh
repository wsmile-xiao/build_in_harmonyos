#!/bin/sh
# test_package/test.sh - HarmonyOS functional consumer test for gnubatch 1.11.
# Usage: test.sh <package_folder>
#
# PKGDIR (argv $1) is authoritative: resolved by test_package/conanfile.py
# from the gnubatch package folder. Layout: bin/ (gbch-* user front-ends),
# libexec/gnubatch/ (btsched/btpwchk/... internal programs), sbin/
# (gbch-passwd/gbch-hostedit/... helpers), lib/ (libgnubatch_int/client/
# curs .so, on LD_LIBRARY_PATH via conanrun).
#
# OHOS readonly_tmp hardening: /tmp on the device is read-only (erofs) and
# the device /bin/sh materializes $(...) command substitution in hardcoded
# /tmp (ignoring TMPDIR), so this script contains ZERO $(...) / backticks.
# Username extraction uses cut into a file + read; counting uses $(( ))
# (parser-internal, no temp file).
#
# Upstream test audit: gnubatch-1.11.tar.gz (sha256
# f69129ecfab1e1d8f5b6ef802388b3adb842f5195a025eea16e955d0b5094ba9,
# 1340 entries) ships NO test suite: no tests/ or test/ directory, zero
# *test* file names, no TESTS/check_PROGRAMS in any Makefile.in, no
# AC_CONFIG_TESTDIR/testsuite in configure.ac, and the top-level
# Makefile.in defines no check target at all (make check = "No rule to
# make target"). See test_package/MANIFEST.yml.
#
# The seven cases below are NEW HarmonyOS functional consumer cases over
# the real packaged binaries; cases 4-7 form a genuine roundtrip through
# gnubatch's password subsystem (gbch-passwd writes the same gbpwfile
# format that btpwchk and btsched authenticate against).
set -u

PKGDIR="${1:-}"

if [ -n "${TMPDIR:-}" ] && [ -d "$TMPDIR" ]; then
    :
elif [ -n "${TMP:-}" ] && [ -d "$TMP" ]; then
    TMPDIR="$TMP"
elif [ -n "${TEMP:-}" ] && [ -d "$TEMP" ]; then
    TMPDIR="$TEMP"
elif [ -n "${HOME:-}" ] && [ -d "$HOME" ]; then
    TMPDIR="$HOME/tmp"
else
    TMPDIR="$PWD/tmp"
fi
mkdir -p "$TMPDIR" 2>/dev/null || true
export TMPDIR
export TMP="$TMPDIR"
export TEMP="$TMPDIR"
export TEMPDIR="$TMPDIR"

# --- OHOS device fixture: synthetic passwd identity (see pwshim.c) --------
# The invoking uid has no /etc/passwd entry, so gbch-passwd's
# getpwuid(getuid()) path cannot resolve the account name (it exits 4:
# "Unable to find current uid <n> in pw file"), while its -u path needs
# root. Compile the LD_PRELOAD fixture (source path supplied by
# test_package/conanfile.py) so cases 4-7 can run the real crypt/gbpwfile
# round trip. Empty PWLD = no fixture (cases 4-7 then fail as before).
PWLD=""
PWSHIM_SO="$TMPDIR/pwshim.so"
if [ -n "${GNUBATCH_PWSHIM_SRC:-}" ] && [ -f "${GNUBATCH_PWSHIM_SRC:-}" ]; then
    for CCQ in "${CC:-}" clang cc gcc /data/service/hnp/bin/clang \
               "$HOME/usr/local/bin/clang" "$HOME/.harmonybrew/bin/clang"; do
        [ -n "$CCQ" ] || continue
        if "$CCQ" -shared -fPIC -o "$PWSHIM_SO" "$GNUBATCH_PWSHIM_SRC" \
               >"$TMPDIR/pwshim.log" 2>&1; then
            PWLD="$PWSHIM_SO"
            break
        fi
    done
fi
if [ -n "$PWLD" ]; then
    echo "[test] passwd-identity fixture built: $PWLD"
else
    echo "[test] WARN: passwd-identity fixture unavailable; cases 4-7 may fail"
fi

PASS_COUNT=0
FAIL_COUNT=0

fail() {
    echo 'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"autotools","command":"make check","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0,"reason":"gnubatch-1.11.tar.gz audited (sha256 f69129ecfab1e1d8f5b6ef802388b3adb842f5195a025eea16e955d0b5094ba9, 1340 entries): no tests/ or test/ directory, no *test* named files, no TESTS/check_PROGRAMS in any Makefile.in, no AC_CONFIG_TESTDIR/testsuite in configure.ac, and top-level Makefile.in has no check target (make check would fail with .No rule to make target.), so there is no upstream check command to run."}'
    echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"/bin/sh test.sh","discovered":7,"passedCount":0}'
    exit 1
}

echo "[test] gnubatch consumer functional test (pkgdir='${PKGDIR:-}')"

if [ -z "$PKGDIR" ] || [ ! -d "$PKGDIR" ]; then
    echo "[test] FAIL: package dir not resolved"
    fail
fi

BINDIR="$PKGDIR/bin"
INTDIR="$PKGDIR/libexec/gnubatch"
SBINDIR="$PKGDIR/sbin"

if [ ! -x "$BINDIR/gbch-hols" ]; then
    echo "[test] FAIL: $BINDIR/gbch-hols missing or not executable"
    ls -la "$BINDIR" 2>&1 || true
    fail
fi
if [ ! -x "$INTDIR/btpwchk" ]; then
    echo "[test] FAIL: $INTDIR/btpwchk missing or not executable"
    ls -la "$INTDIR" 2>&1 || true
    fail
fi
if [ ! -x "$SBINDIR/gbch-passwd" ]; then
    echo "[test] FAIL: $SBINDIR/gbch-passwd missing or not executable"
    ls -la "$SBINDIR" 2>&1 || true
    fail
fi
echo "[test] bin listing:"
ls -la "$BINDIR" 2>&1 || true

PWFILE="$TMPDIR/gbpwfile"
rm -f "$PWFILE" "$TMPDIR/tn_user" "$TMPDIR"/c*.out "$TMPDIR"/c*.err 2>/dev/null || true

# ---------------------------------------------------------------- case 1
# Version banner of an internal program: configure-time version
# substitution (GNU_BATCH_VERSION_STRING) + libgnubatch_int .so
# resolution at run time.
echo "[test] case 1: btpwchk_version_banner"
"$INTDIR/btpwchk" --version >"$TMPDIR/c1.out" 2>"$TMPDIR/c1.err"
RC=$?
if [ "$RC" -eq 0 ] && grep -q "GNUbatch version 1.11" "$TMPDIR/c1.err" 2>/dev/null; then
    echo "ok: btpwchk_version_banner (rc=0, 'GNUbatch version 1.11' on stderr)"
    PASS_COUNT=$((PASS_COUNT+1))
else
    echo "FAIL: btpwchk_version_banner (rc=$RC, expected rc=0 + version banner)"
    cat "$TMPDIR/c1.out" "$TMPDIR/c1.err" 2>/dev/null || true
    FAIL_COUNT=$((FAIL_COUNT+1))
fi

# ---------------------------------------------------------------- case 2
# Version banner of a curses front-end: exercises the ncurses shared
# library chain (conan ncurses .so via conanrun LD_LIBRARY_PATH) plus
# the internal libgnubatch_curs/libgnubatch_int .so set.
echo "[test] case 2: gbch_hols_version_banner"
"$BINDIR/gbch-hols" --version >"$TMPDIR/c2.out" 2>"$TMPDIR/c2.err"
RC=$?
if [ "$RC" -eq 0 ] && grep -q "GNUbatch version 1.11" "$TMPDIR/c2.err" 2>/dev/null; then
    echo "ok: gbch_hols_version_banner (rc=0, curses front-end runs)"
    PASS_COUNT=$((PASS_COUNT+1))
else
    echo "FAIL: gbch_hols_version_banner (rc=$RC, expected rc=0 + version banner)"
    cat "$TMPDIR/c2.out" "$TMPDIR/c2.err" 2>/dev/null || true
    FAIL_COUNT=$((FAIL_COUNT+1))
fi

# ---------------------------------------------------------------- case 3
# gbch-passwd usage error path: invalid option prints Usage and exits 1
# (util/gbpasswd.c getopt '?' branch). -f forces past the root-password
# guard so later cases are independent of the invoking uid.
echo "[test] case 3: gbch_passwd_usage_error"
"$SBINDIR/gbch-passwd" -Z >"$TMPDIR/c3.out" 2>"$TMPDIR/c3.err"
RC=$?
if [ "$RC" -eq 1 ] && grep -q "Usage" "$TMPDIR/c3.err" 2>/dev/null; then
    echo "ok: gbch_passwd_usage_error (rc=1, Usage on stderr)"
    PASS_COUNT=$((PASS_COUNT+1))
else
    echo "FAIL: gbch_passwd_usage_error (rc=$RC, expected rc=1 + Usage)"
    cat "$TMPDIR/c3.out" "$TMPDIR/c3.err" 2>/dev/null || true
    FAIL_COUNT=$((FAIL_COUNT+1))
fi

# ---------------------------------------------------------------- case 4
# gbch-passwd creates a password file for the invoking user
# (getpwuid fallback path, -F target file, -p non-interactive).
echo "[test] case 4: gbch_passwd_file_create"
LD_PRELOAD="$PWLD" "$SBINDIR/gbch-passwd" -f -F "$PWFILE" -p testsecret1 >"$TMPDIR/c4.out" 2>"$TMPDIR/c4.err"
RC=$?
if [ "$RC" -eq 0 ] && [ -s "$PWFILE" ] && grep -q ":" "$PWFILE" 2>/dev/null; then
    echo "ok: gbch_passwd_file_create (rc=0, pwfile written)"
    PASS_COUNT=$((PASS_COUNT+1))
else
    echo "FAIL: gbch_passwd_file_create (rc=$RC, expected rc=0 + non-empty pwfile)"
    cat "$TMPDIR/c4.out" "$TMPDIR/c4.err" 2>/dev/null || true
    FAIL_COUNT=$((FAIL_COUNT+1))
fi

# GBUSER = the account name gbch-passwd wrote (first field of gbpwfile).
cut -d: -f1 "$PWFILE" >"$TMPDIR/tn_user" 2>/dev/null || true
GBUSER=""
read GBUSER <"$TMPDIR/tn_user" || true
echo "[test] pwfile user='${GBUSER:-}'"

# ---------------------------------------------------------------- case 5
# btpwchk correct-password roundtrip: SPROGDIR redirects XIPWFILE
# ("${SPROGDIR-@pkgexecdir@}/gbpwfile", src/hdrs/infiles.h.in) so btpwchk
# authenticates against the file case 4 just created; crypt() check must
# print '0' and exit 0.
echo "[test] case 5: btpwchk_correct_password"
if [ -n "$GBUSER" ]; then
    echo testsecret1 | LD_PRELOAD="$PWLD" SPROGDIR="$TMPDIR" "$INTDIR/btpwchk" "$GBUSER" >"$TMPDIR/c5.out" 2>"$TMPDIR/c5.err"
    RC=$?
else
    RC=99
fi
if [ "$RC" -eq 0 ] && grep -q "^0$" "$TMPDIR/c5.out" 2>/dev/null; then
    echo "ok: btpwchk_correct_password (rc=0, output '0')"
    PASS_COUNT=$((PASS_COUNT+1))
else
    echo "FAIL: btpwchk_correct_password (rc=$RC, expected rc=0 + '0')"
    cat "$TMPDIR/c5.out" "$TMPDIR/c5.err" 2>/dev/null || true
    FAIL_COUNT=$((FAIL_COUNT+1))
fi

# ---------------------------------------------------------------- case 6
# btpwchk wrong-password rejection: same roundtrip, mismatching secret
# must print '1' and exit 1.
echo "[test] case 6: btpwchk_wrong_password"
if [ -n "$GBUSER" ]; then
    echo wrongpass9 | LD_PRELOAD="$PWLD" SPROGDIR="$TMPDIR" "$INTDIR/btpwchk" "$GBUSER" >"$TMPDIR/c6.out" 2>"$TMPDIR/c6.err"
    RC=$?
else
    RC=99
fi
if [ "$RC" -eq 1 ] && grep -q "^1$" "$TMPDIR/c6.out" 2>/dev/null; then
    echo "ok: btpwchk_wrong_password (rc=1, output '1')"
    PASS_COUNT=$((PASS_COUNT+1))
else
    echo "FAIL: btpwchk_wrong_password (rc=$RC, expected rc=1 + '1')"
    cat "$TMPDIR/c6.out" "$TMPDIR/c6.err" 2>/dev/null || true
    FAIL_COUNT=$((FAIL_COUNT+1))
fi

# ---------------------------------------------------------------- case 7
# btpwchk unknown-user rejection: user absent from the pwfile must
# print '5' and exit 5 (get_pwfile miss path).
echo "[test] case 7: btpwchk_unknown_user"
echo whatever1 | LD_PRELOAD="$PWLD" SPROGDIR="$TMPDIR" "$INTDIR/btpwchk" "ghost_nouser_x" >"$TMPDIR/c7.out" 2>"$TMPDIR/c7.err"
RC=$?
if [ "$RC" -eq 5 ] && grep -q "^5$" "$TMPDIR/c7.out" 2>/dev/null; then
    echo "ok: btpwchk_unknown_user (rc=5, output '5')"
    PASS_COUNT=$((PASS_COUNT+1))
else
    echo "FAIL: btpwchk_unknown_user (rc=$RC, expected rc=5 + '5')"
    cat "$TMPDIR/c7.out" "$TMPDIR/c7.err" 2>/dev/null || true
    FAIL_COUNT=$((FAIL_COUNT+1))
fi

# Upstream audit marker (authority: test_package/MANIFEST.yml).
echo 'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"autotools","command":"make check","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0,"reason":"gnubatch-1.11.tar.gz audited (sha256 f69129ecfab1e1d8f5b6ef802388b3adb842f5195a025eea16e955d0b5094ba9, 1340 entries): no tests/ or test/ directory, no *test* named files, no TESTS/check_PROGRAMS in any Makefile.in, no AC_CONFIG_TESTDIR/testsuite in configure.ac, no check target in top-level Makefile.in, so there is no upstream check command to run."}'

echo "[test] summary: pass=$PASS_COUNT fail=$FAIL_COUNT (of 7)"

if [ "$FAIL_COUNT" -eq 0 ] && [ "$PASS_COUNT" -eq 7 ]; then
    echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"/bin/sh test.sh","discovered":7,"passedCount":7}'
    exit 0
else
    echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"/bin/sh test.sh","discovered":7,"passedCount":'"$PASS_COUNT"'}'
    exit 1
fi
