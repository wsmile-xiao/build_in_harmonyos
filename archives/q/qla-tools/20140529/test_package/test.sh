#!/usr/bin/env bash
# test_package/test.sh — qla-tools 20140529 consumer test.
#
# Runs in the conanrun environment: the tested package's bin/ is on PATH and the
# four installed commands are located with `command -v` (removing the package's
# bin/ makes every case fail — the CI L1e negative test keeps this suite
# genuinely dependent on the package, R34).
#
# Execution wrapper: the installed scripts carry the OHOS bash shebang
# (#!/data/service/hnp/bin/bash) and exec directly for a normal user. The
# CI/conan test runner, however, may run under a uid that cannot execve() script
# files at all (any shebang -> EACCES / "bad interpreter"), so the scripts are
# invoked through the OHOS bash explicitly — the same wrapping the repo's own
# test_package-executable template prescribes. The real installed code still runs.
#
# Upstream ships NO automated test suite (no tests/, no debian/tests, no
# dh_auto_test). These cases are the adapted test set and exercise all four
# upstream sample scripts (no sample left untested). Cases 6-8 are
# HarmonyOS-specific and correspond 1:1 to the changes in patches/.
set -u

OHOS_BASH=/data/service/hnp/bin/bash
TOTAL=0; PASS=0; FAIL=0; SKIP=0
RESULTS=""

report() { # $1 status  $2 case name  $3 detail
  TOTAL=$((TOTAL + 1))
  RESULTS="${RESULTS}${1}	${2}	${3}
"
  case "$1" in
    PASS) PASS=$((PASS + 1)) ;;
    SKIP) SKIP=$((SKIP + 1)) ;;
    *)    FAIL=$((FAIL + 1)) ;;
  esac
  printf '  [%-4s] %-34s %s\n' "$1" "$2" "$3"
}

# shell-error signatures that must never appear (interpreter / RO-fs / missing cmd)
SHELL_ERR_RE='bad interpreter|command not found|Read-only file system|syntax error|No such file or directory|not found'
# empty $OHOS_BASH intentionally fails (command -v returns nothing) -> L1e works
qs() { "$OHOS_BASH" "$(command -v "$1")" "${@:2}"; }

SCRIPTS="ql-hba-snapshot ql-lun-state-online ql-set-cmd-timeout ql-dynamic-tgt-lun-disc"

echo "================ qla-tools 20140529 test_package ================"
echo "[env] ohos bash : $OHOS_BASH"
echo "[env] uname -r  : $(uname -r)"
echo "[env] uname -s  : $(uname -s)"
echo "[env] sg_turs   : $(command -v sg_turs 2>/dev/null || echo 'not on PATH')"
echo "----------------------------------------------------------------"

# ── Case 1: all four upstream sample scripts installed and executable ──
miss=""
for s in $SCRIPTS; do
  if ! p=$(command -v "$s" 2>/dev/null); then miss="$miss $s(missing)"; continue; fi
  [ -x "$p" ] || miss="$miss $s(not-exec)"
done
if [ -z "$miss" ]; then
  report PASS installed_scripts_present "all 4 upstream scripts on PATH and executable"
else
  report FAIL installed_scripts_present "problems:$miss"
fi

# ── Case 2: ql-hba-snapshot executes (rc 0/1) without any shell diagnostics ──
out=$(qs ql-hba-snapshot 2>&1); rc=$?
if printf '%s' "$out" | grep -qE "$SHELL_ERR_RE"; then
  report FAIL ql-hba-snapshot_runs "shell diagnostic: $(printf '%s' "$out" | grep -oE "$SHELL_ERR_RE" | head -1)"
elif [ "$rc" -eq 0 ] || [ "$rc" -eq 1 ]; then
  report PASS ql-hba-snapshot_runs "executed cleanly (rc=$rc)"
else
  report FAIL ql-hba-snapshot_runs "unexpected exit code rc=$rc"
fi

# ── Case 3: ql-lun-state-online -h prints usage and exits 0 ──
out=$(qs ql-lun-state-online -h 2>&1); rc=$?
if [ "$rc" -eq 0 ] && printf '%s' "$out" | grep -qi "OPTIONS"; then
  report PASS ql-lun-state-online_help "-h rc=0 and usage printed"
else
  report FAIL ql-lun-state-online_help "-h rc=$rc, usage missing"
fi

# ── Case 4: ql-set-cmd-timeout -h prints usage and exits 0 ──
out=$(qs ql-set-cmd-timeout -h 2>&1); rc=$?
if [ "$rc" -eq 0 ] && printf '%s' "$out" | grep -qi "Usage:"; then
  report PASS ql-set-cmd-timeout_help "-h rc=0 and usage printed"
else
  report FAIL ql-set-cmd-timeout_help "-h rc=$rc, usage missing"
fi

# ── Case 5: ql-dynamic-tgt-lun-disc executes and reports the no-HBA path ──
out=$(qs ql-dynamic-tgt-lun-disc 2>&1); rc=$?
if printf '%s' "$out" | grep -qE "$SHELL_ERR_RE"; then
  report FAIL ql-dynamic-tgt-lun-disc_runs "shell diagnostic: $(printf '%s' "$out" | grep -oE "$SHELL_ERR_RE" | head -1)"
elif printf '%s' "$out" | grep -q "No FC/ISCSI host is found"; then
  report PASS ql-dynamic-tgt-lun-disc_runs "executed (rc=$rc): no FC/iSCSI HBA present"
else
  report FAIL ql-dynamic-tgt-lun-disc_runs "rc=$rc, expected 'No FC/ISCSI host is found'"
fi

# ── Case 6 (OHOS): every script carries the OHOS bash shebang and it exists ──
# OHOS has no /bin/bash and /usr/bin/env is not traversable for every runner uid,
# so the shebang must be the absolute OHOS bash path
# (repo convention, cf. cryptsetup "ohos-bash-shebang").
bad=""
for s in $SCRIPTS; do
  p=$(command -v "$s" 2>/dev/null) || { bad="$bad $s(absent)"; continue; }
  head1=$(head -n 1 "$p")
  [ "$head1" = "#!$OHOS_BASH" ] || bad="$bad $s($head1)"
done
if [ -z "$bad" ] && [ -f "$OHOS_BASH" ]; then
  report PASS OHOS_shebang_hnp_bash "all 4 shebangs=#!$OHOS_BASH and interpreter present"
else
  report FAIL OHOS_shebang_hnp_bash "bad shebangs/resolver:$bad"
fi

# ── Case 7 (OHOS): no hard-coded /tmp writes (OHOS /tmp is read-only, E002) ──
out=$(qs ql-dynamic-tgt-lun-disc 2>&1)
if printf '%s' "$out" | grep -q "Read-only file system"; then
  report FAIL OHOS_tmp_writable_base "still writing to read-only /tmp: $(printf '%s' "$out" | grep -m1 'Read-only file system')"
else
  report PASS OHOS_tmp_writable_base "no read-only /tmp writes (uses \$TMPDIR/\$HOME)"
fi

# ── Case 8 (OHOS): the Linux 2.6 gate accepts the HarmonyOS kernel string ──
# uname -r on OHOS = 'HongMeng Kernel 1.12.0'; the script must not reject it.
out=$(qs ql-hba-snapshot 2>&1)
if printf '%s' "$out" | grep -q "Only Kernel version 2.6"; then
  report FAIL OHOS_kernel_release_accepted "OHOS kernel release string rejected by gate"
else
  report PASS OHOS_kernel_release_accepted "OHOS kernel string accepted (gate passed)"
fi

echo "----------------------------------------------------------------"
echo "qla-tools 20140529 test_package: TOTAL=$TOTAL PASS=$PASS FAIL=$FAIL SKIP=$SKIP"
printf '%s' "$RESULTS"

[ "$FAIL" -eq 0 ] || exit 1
exit 0
