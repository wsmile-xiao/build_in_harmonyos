#!/usr/bin/env bash
# test_package/test.sh — behavioural test for the installed anacron 2.3.
#
# Everything lives under $PWD (the conan build folder). /tmp is read-only on
# OHOS/HarmonyOS (E002), so it must never be used as scratch.
# -o pipefail：让 `cmd | head/grep … || fail` 这类守卫能捕获管道**首段**的非零退出
# （无 pipefail 时 `||` 只看管道末命令，`anacron -V | head -1` 里 anacron 挂掉也会被判绿）。
set -uo pipefail

fail() { echo "FAIL: $*" >&2; exit 1; }
pass() { echo "PASS: $*"; }

SCRATCH="${ANACRON_TP_SCRATCH:-$PWD/anacron-tp-scratch}"
rm -rf "$SCRATCH"
mkdir -p "$SCRATCH/spool" "$SCRATCH/etc" || fail "cannot create scratch under $PWD"

ANACRON="$(command -v anacron || true)"
[ -n "$ANACRON" ] || fail "anacron not on PATH (conanrun env broken)"
pass "anacron resolves to $ANACRON"

# ---- 1. version banner -------------------------------------------------
ver="$("$ANACRON" -V 2>&1 | head -1)" || fail "anacron -V exited non-zero"
case "$ver" in
  "Anacron 2.3") pass "version banner: $ver" ;;
  *) fail "unexpected version banner: $ver" ;;
esac

# ---- 2. anacrontab parsing + real job execution + spool timestamp -------
cat > "$SCRATCH/job.sh" <<EOF
#!/bin/sh
echo ran > "$SCRATCH/ran.marker"
EOF
cat > "$SCRATCH/etc/anacrontab" <<EOF
SHELL=/bin/sh
PATH=/usr/local/bin:/usr/bin:/bin
1   0   smokejob   /bin/sh $SCRATCH/job.sh
EOF

out="$(ANACRON_SPOOL="$SCRATCH/spool" "$ANACRON" -n -f -d -t "$SCRATCH/etc/anacrontab" 2>&1)"
rc=$?
echo "$out"
[ "$rc" -eq 0 ] || fail "anacron -n -f -d exited $rc"
echo "$out" | grep -q "Will run job" || fail "anacrontab job was not scheduled"
pass "anacrontab parsed and job scheduled"

# anacron exits only after wait_children(), so the job must be done here.
[ -f "$SCRATCH/ran.marker" ] || fail "job body did not execute (no marker file)"
pass "job executed via fork/exec + /bin/sh -c"

[ -f "$SCRATCH/spool/smokejob" ] || fail "spool timestamp file missing"
pass "spool timestamp created ($SCRATCH/spool/smokejob)"

# ---- 3. ANACRON_SPOOL override is honoured -----------------------------
out2="$(ANACRON_SPOOL="$SCRATCH/other-spool" "$ANACRON" -n -f -d -t "$SCRATCH/etc/anacrontab" 2>&1)"
rc2=$?
# other-spool does not exist -> anacron must fail loudly, proving the
# override really drives chdir() instead of the compiled-in default.
[ "$rc2" -ne 0 ] || fail "anacron accepted a non-existent ANACRON_SPOOL"
echo "$out2" | grep -qi "Can't chdir" || fail "expected 'Can't chdir' for missing spool, got: $out2"
pass "ANACRON_SPOOL override reaches chdir()"

# ---- 4. -u updates timestamps without running the job ------------------
rm -f "$SCRATCH/ran.marker"
out3="$(ANACRON_SPOOL="$SCRATCH/spool" "$ANACRON" -n -f -d -u -t "$SCRATCH/etc/anacrontab" 2>&1)"
rc3=$?
[ "$rc3" -eq 0 ] || fail "anacron -u exited $rc3"
[ ! -f "$SCRATCH/ran.marker" ] || fail "-u must not run the job"
echo "$out3" | grep -q "Updated timestamp" || fail "missing 'Updated timestamp' output"
pass "-u updates the timestamp without running the job"

echo "ALL TESTS PASSED"
