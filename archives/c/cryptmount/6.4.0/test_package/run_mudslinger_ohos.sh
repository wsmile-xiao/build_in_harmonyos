#!/bin/sh
# Run the safe, unprivileged cases from the upstream mudslinger function set.
# This keeps the upstream assertions intact while replacing only its launcher
# assumptions (/tmp, /bin/su and system user switching).
set -eu

testing_dir=$1
cryptmount_bin=$2
scratch=$3
mkdir -p "$scratch"
driver="$scratch/mudslinger-functions.sh"
report="$scratch/mudslinger-report.txt"
details="$scratch/mudslinger-details.txt"
runner_source="$testing_dir/mudslinger"
if [ ! -f "$runner_source" ]; then
    runner_source="$testing_dir/mudslinger.in"
fi
[ -f "$runner_source" ] || { echo "missing upstream mudslinger runner in $testing_dir" >&2; exit 2; }

sed '/^# Main program$/,$d' "$runner_source" > "$driver"
cat >> "$driver" <<'RUNNER'
set +e
CM="$CRYPTMOUNT_BIN"
USER1=currentUser
USER2=currentUser
SU_p="$SCRATCH/su-current-user.sh"
LOOPDEV=/dev/null
LOOPDEV2=/dev/null

for tc in version binary null listing defaults; do
    TMPDIR="$SCRATCH/case-$tc"
    mkdir -p "$TMPDIR/mnt"
    NTESTS_RUN=0
    NTESTS_FAILED=0
    NTESTS_PASSED=0
    NTESTS_ABORTED=0
    printf 'CASE_START=%s\n' "$tc"
    "test_$tc"
    printf 'CASE_RESULT=%s RUN=%s PASS=%s FAIL=%s ABORT=%s\n' \
        "$tc" "$NTESTS_RUN" "$NTESTS_PASSED" "$NTESTS_FAILED" "$NTESTS_ABORTED"
done
RUNNER

cat > "$scratch/su-current-user.sh" <<'SU_SHIM'
#!/bin/sh
shift
[ "$1" = "-c" ] || exit 125
shift
exec sh -c "$1"
SU_SHIM
chmod +x "$scratch/su-current-user.sh"

export CRYPTMOUNT_BIN="$cryptmount_bin"
export SCRATCH="$scratch"
ulimit -c 0
if ! bash 3>"$details" "$driver" >"$report" 2>&1; then
    cat "$report"
    exit 1
fi
cat "$report"

passed=$(grep -c '^CASE_RESULT=.* PASS=1 FAIL=0 ABORT=0$' "$report" || true)
aborted=$(grep -c '^CASE_RESULT=binary RUN=1 PASS=0 FAIL=0 ABORT=1$' "$report" || true)
failed=$(grep -c '^CASE_RESULT=.* FAIL=[1-9]' "$report" || true)
if [ "$passed" -ne 4 ] || [ "$aborted" -ne 1 ] || [ "$failed" -ne 0 ]; then
    cat "$details"
    echo "UPSTREAM_SAFE_SUITE_UNEXPECTED: passed=$passed aborted=$aborted failed=$failed"
    exit 1
fi
echo "UPSTREAM_SAFE_SUITE: 4 passed; test_binary aborted at unsupported BLKGETSIZE ioctl; 0 failed"
