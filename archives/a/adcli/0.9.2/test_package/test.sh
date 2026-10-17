#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for adcli 0.9.2 executable
# Runs in conanrun env (PATH includes installed bin/ — Conan 2
# AutotoolsToolchain forces --sbindir=${prefix}/bin, so the upstream
# sbin_PROGRAMS lands in <pkg>/bin/, matching package_info.bindirs)
set -eu

# HMFS/HMDFS: /tmp is a read-only erofs mount and the conan build-tree cwd may
# be inaccessible (getcwd fails — HMBS platform diagnosis [shell_getcwd] /
# [readonly_tmp], same as the addchain/aaphoto recipes). Move to the injected
# writable scratch dir and never write to /tmp.
SCRATCH="${TMPDIR:-${TMP:-${TEMP:-$HOME/tmp}}}"
mkdir -p "$SCRATCH"
cd "$SCRATCH"

ADCLI_BIN="${ADCLI_BIN:-adcli}"

echo "[test] $ADCLI_BIN --help"
HELP_OUT="$("$ADCLI_BIN" --help 2>&1)" || {
    echo "❌ adcli --help failed (exit $?)"
    exit 1
}
echo "$HELP_OUT" | grep -q "usage: adcli" || {
    echo "❌ adcli --help output missing usage line"
    exit 1
}

echo "[test] $ADCLI_BIN bogus-command (rejects unknown command)"
set +e
BOGUS_OUT="$("$ADCLI_BIN" bogus-command 2>&1)"
RC=$?
set -e
if [ "$RC" -ne 2 ]; then
    echo "❌ adcli bogus-command: expected exit 2, got $RC"
    exit 1
fi
echo "$BOGUS_OUT" | grep -q "not a valid adcli command" || {
    echo "❌ adcli bogus-command: expected error message"
    exit 1
}

echo "[test] all adcli executable checks PASSED"
exit 0
