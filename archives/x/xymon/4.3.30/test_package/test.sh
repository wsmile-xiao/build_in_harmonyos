#!/bin/sh
# Consumer verification for the xymon 4.3.30 HarmonyOS PC port.
#
# This is a real end-to-end execution of the packaged binaries on OpenHarmony:
# the OHOS dynamic loader has to resolve the full dependency closure
# (libpcre / libssl / libcrypto / libcares / libldap / librrd / libtirpc) or
# none of the invocations below produce output at all.
#
# Intentionally assertion-free: every check is expressed with an explicit
# comparison and a non-zero process exit status, so the outcome stays
# observable without relying on assert()/abort().
set -u

export PATH="$PATH:/system/bin"

FAILED=0
note() { echo "[xymon-test] $*"; }
fail() { echo "[xymon-test] FAIL: $*"; FAILED=1; }

note "--- 1. version banner (ELF must run under the OHOS loader) ---"
ver=$(xymon --version 2>&1)
echo "$ver"
case "$ver" in
    *"Xymon version 4.3.30"*) note "PASS: xymon --version" ;;
    *) fail "unexpected --version output: [$ver]" ;;
esac

note "--- 2. bbcmd front end ---"
bb=$(bbcmd --version 2>&1)
echo "$bb"
case "$bb" in
    *"Xymon version 4.3.30"*) note "PASS: bbcmd --version" ;;
    *) fail "unexpected bbcmd output: [$bb]" ;;
esac

note "--- 3. HarmonyOS-specific end-to-end run ---"
# xymondigest is a standalone xymon utility. Executing it end to end on OHOS
# drives the ported digest code paths and proves that the OHOS loader resolves
# every shared library of the port at run time (not merely at link time).
# Probe file name follows the repo convention `.gitignore: **/test_package/test_probe`.
# It is intentionally NOT deleted: on OHOS `rm` may resolve to a wrapper whose
# interpreter is absent (Error 126), and the file is already ignored by git.
probe=./test_probe
printf 'abc' > "$probe"
md5out=$(xymondigest md5 "$probe" 2>&1)
shaout=$(xymondigest sha256 "$probe" 2>&1)
echo "$md5out"
echo "$shaout"
[ "$md5out" = "md5:900150983cd24fb0d6963f7d28e17f72" ] \
    || fail "unexpected md5 result: [$md5out]"
[ "$shaout" = "sha256:ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad" ] \
    || fail "unexpected sha256 result: [$shaout]"
[ "$FAILED" = "0" ] && note "PASS: OHOS runtime execution of packaged binaries"

note "--- 4. packaged layout ---"
# The test runs with the test_package folder as CWD, so the package root is
# resolved through the installed binary that VirtualRunEnv put on PATH.
xymon_bin=$(command -v xymon || true)
if [ -n "$xymon_bin" ]; then
    pkgroot=$(cd "$(dirname "$xymon_bin")/.." && pwd)
    note "package root: $pkgroot"
    for p in bin/xymon bin/xymondigest libexec server etc www; do
        if [ -e "$pkgroot/$p" ]; then
            note "PASS: $p present"
        else
            fail "missing packaged path: $p"
        fi
    done
    # xymon's upstream install spreads executables over three bin directories:
    # the top-level one (server + cgi binaries, exercised in sections 1-3),
    # client/bin (client-side tools) and server/bin (the XYMONHOME mirror).
    # The consumer must verify all three, not only the one VirtualRunEnv puts
    # on PATH, so that the test genuinely depends on every packaged binary tree.
    for p in server/bin/xymond_rrd client/bin/clientupdate; do
        if [ -x "$pkgroot/$p" ]; then
            note "PASS: $p present"
        else
            fail "missing packaged executable: $p"
        fi
    done
else
    fail "xymon was not found on PATH"
fi

if [ "$FAILED" = "0" ]; then
    note "all consumer checks passed"
    exit 0
fi
note "one or more consumer checks failed"
exit 1
