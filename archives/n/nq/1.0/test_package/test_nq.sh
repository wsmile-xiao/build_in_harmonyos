#!/data/service/hnp/bin/bash
# test_package/test_nq.sh — functional queue smoke test for packaged nq tools.
# Runs in the conanrun environment (PATH includes the installed bin/ dir).
# Really executes the packaged binaries; fails loudly if any assertion fails.
set -u

# Belt & braces: keep the standard system dirs on PATH so the background job
# (sh) and status helpers resolve regardless of the caller's environment.
export PATH="/data/service/hnp/bin:/usr/bin:/bin:${PATH}"

QDIR="nqtest.$$"
mkdir -p "$QDIR"
cd "$QDIR" || exit 1

n_ok=0
n_fail=0
check() {
  local msg="$1"
  shift
  if eval "$@" >/dev/null 2>&1; then
    echo "ok - $msg"
    n_ok=$((n_ok + 1))
  else
    echo "not ok - $msg"
    n_fail=$((n_fail + 1))
  fi
}

echo "1..6"

# 1) enqueue a real job that echoes a marker to its log
check "enqueue a real job with nq" \
  'job=$(nq sh -c "echo NQ_JOB_RAN_OK"); test -n "$job"'

# 2) wait for the job to finish (nq -w, flock-based ordering)
check "wait for the job with nq -w" 'nq -w "$job"'

# 3) the marker was really produced and captured in the job log
check "job log contains command output" 'grep -q NQ_JOB_RAN_OK "$job"'

# 4) the log records that the job exited with status 0
check "job log records exited-with-status-0" 'grep -q "exited with status 0" "$job"'

# 5) nqtail prints the completed job's log
check "nqtail prints the completed job log" 'nqtail "$job" | grep -q NQ_JOB_RAN_OK'

# 6) nqterm wrapper is installed and executable
check "nqterm wrapper is executable" 'test -x "$(command -v nqterm)"'

cd ..
rm -rf "$QDIR"
echo "# nq functional assertions: pass=$n_ok fail=$n_fail"
[ "$n_fail" -eq 0 ]
