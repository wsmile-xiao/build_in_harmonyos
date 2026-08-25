#!/bin/sh
# test_package/test.sh — smoke test for hf-mount executable
# Runs in conanrun env (PATH includes installed bin/)
# Counts each real case and emits the HMBS_TEST_PACKAGE_RESULT marker.
#
# hf-mount is the management CLI: `hf-mount --version` prints the CLI
# version, `hf-mount --help` shows USAGE, and `hf-mount status` lists
# running daemons (none expected in the sandbox). The NFS/FUSE daemon
# backends (`hf-mount-nfs`, `hf-mount-fuse`) are not exercised here —
# they need a mount point + network to huggingface.co, unavailable in
# the offline OHOS PC sandbox; the consumer test validates the
# management CLI the user actually invokes.
#
# HMBS platform diagnostic shell_getcwd: HNP bash in HMFS/HMDFS working
# dir fails getcwd() at startup and prints a harmless `shell-init:` line
# to stderr. The harness itself runs under the injected /bin/sh
# (CONFIG_SHELL) and is unaffected; the status case below uses sh-internal
# redirection only, no bash spawn, so no artifact to strip.
set -uo pipefail

PASS=0
FAIL=0

# cd to a writable directory (HMBS TMPDIR; OHOS /tmp is read-only)
cd "${TMPDIR:-${TMP:-${TEMP:-/tmp}}}"

echo "[test] hf-mount --version"
VERSION_OUT=$(hf-mount --version 2>&1)
if printf '%s' "$VERSION_OUT" | grep -q "hf-mount 0.9.0"; then
    PASS=$((PASS + 1))
    echo "[ok] --version prints 'hf-mount 0.9.0'"
else
    FAIL=$((FAIL + 1))
    echo "[fail] --version output unexpected: $VERSION_OUT"
fi

echo "[test] hf-mount --help"
HELP_OUT=$(hf-mount --help 2>&1)
if printf '%s' "$HELP_OUT" | grep -iq "Usage:"; then
    PASS=$((PASS + 1))
    echo "[ok] --help shows Usage section"
else
    FAIL=$((FAIL + 1))
    echo "[fail] --help output unexpected: $HELP_OUT"
fi

echo "[test] hf-mount status (no running daemons in sandbox)"
STATUS_OUT=$(hf-mount status 2>&1)
RC=$?
if [ "$RC" -eq 0 ] && printf '%s' "$STATUS_OUT" | grep -q "No running daemons"; then
    PASS=$((PASS + 1))
    echo "[ok] status reports 'No running daemons' (rc=0)"
else
    FAIL=$((FAIL + 1))
    echo "[fail] status rc=$RC output: $STATUS_OUT"
fi

echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":$([ "$FAIL" -eq 0 ] && echo true || echo false),\"command\":\"/bin/sh test.sh\",\"discovered\":3,\"passedCount\":$PASS}"

if [ "$FAIL" -ne 0 ]; then
    echo "[fail] $FAIL case(s) failed, $PASS passed"
    exit 1
fi
echo "[ok] all $PASS test_package cases passed"
