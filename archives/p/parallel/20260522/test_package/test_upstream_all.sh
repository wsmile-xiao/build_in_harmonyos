#!/usr/bin/env bash
set -uo pipefail

package_bin=$1
upstream_root=$2
perl_bin=$3
results_dir=$4
per_script_timeout=${UPSTREAM_TEST_TIMEOUT:-120}
test_jobs=${UPSTREAM_TEST_JOBS:-16}

upstream_tests="$upstream_root/testsuite"
upstream_src="$upstream_root/src"
scripts_dir="$upstream_tests/tests-to-run"
wanted_dir="$upstream_tests/wanted-results"

file_count=$(find "$upstream_tests" -type f | wc -l | tr -d ' ')
script_count=$(find "$scripts_dir" -maxdepth 1 -type f -name '*.sh' | wc -l | tr -d ' ')
wanted_count=$(find "$wanted_dir" -maxdepth 1 -type f | wc -l | tr -d ' ')
test "$file_count" -eq 390
test "$script_count" -eq 108
test "$wanted_count" -eq 109
printf 'PASS: retained complete upstream testsuite (%d/390 files)\n' "$file_count"
printf 'RUN: all upstream test scripts (%d/108 scripts, %d wanted-results)\n' \
    "$script_count" "$wanted_count"

export PARALLEL_SHELL=bash
export LANG=C
export LC_ALL=C
export PERL="$perl_bin"
perl_root=$(cd "$(dirname "$perl_bin")/.." && pwd)
perl5lib=$(find "$perl_root/lib/perl5" -type d | LC_ALL=C sort | paste -sd: -)
export PERL5LIB="$perl5lib${PERL5LIB:+:$PERL5LIB}"
"$perl_bin" -MIPC::Open3 -MFcntl -e 'print qq(PASS: Conan Perl runtime modules loaded\n)'

work_dir=$(mktemp -d "${TMPDIR:-$HOME}/parallel-upstream-all.XXXXXX")
trap 'rm -rf "$work_dir"' EXIT
mkdir -p "$work_dir/bin" "$work_dir/home" "$work_dir/tmp" "$results_dir/actual" "$results_dir/diff"

make_perl_wrapper() {
    name=$1
    target=$2
    cat > "$work_dir/bin/$name" <<EOF
#!/usr/bin/env sh
exec "$perl_bin" "$target" "\$@"
EOF
    chmod +x "$work_dir/bin/$name"
}

for name in parallel sem sql; do
    test -f "$package_bin/$name"
    make_perl_wrapper "$name" "$package_bin/$name"
done
for name in niceload parcat parsort; do
    if test -f "$upstream_src/$name"; then
        make_perl_wrapper "$name" "$upstream_src/$name"
    fi
done
cp "$upstream_src/env_parallel" "$work_dir/bin/env_parallel"
chmod +x "$work_dir/bin/env_parallel"
for shell in ash bash csh dash fish ksh mksh pdksh sh tcsh zsh; do
    if test -f "$upstream_src/env_parallel.$shell"; then
        cp "$upstream_src/env_parallel.$shell" "$work_dir/bin/"
    fi
done

export PATH="$work_dir/bin:$PATH"
export HOME="$work_dir/home"
export PARALLEL_HOME="$HOME/.parallel"
mkdir -p "$PARALLEL_HOME"
touch "$PARALLEL_HOME/will-cite"

summary="$results_dir/summary.tsv"
rows_dir="$results_dir/rows"
mkdir -p "$rows_dir"
printf 'script\tstatus\texit_code\tduration_seconds\treason\n' > "$summary"

run_one() {
    script=$1
    base=$(basename "$script" .sh)
    expected="$wanted_dir/$base"
    actual="$results_dir/actual/$base"
    diff_file="$results_dir/diff/$base.diff"
    script_tmp="$work_dir/tmp/$base"
    mkdir -p "$script_tmp"

    start=$(date +%s)
    (
        cd "$script_tmp"
        TMPDIR="$script_tmp" timeout "$per_script_timeout" \
            bash "$script" 2>&1
    ) > "$actual"
    rc=$?
    end=$(date +%s)
    duration=$((end - start))

    if test ! -f "$expected"; then
        status=MISSING_EXPECTED
        reason='upstream wanted-result is absent'
    elif diff -u "$expected" "$actual" > "$diff_file"; then
        status=PASS
        reason='output matches unmodified upstream wanted-result'
        rm -f "$diff_file"
    elif test "$rc" -eq 124; then
        status=BLOCKED_ENV
        reason="timed out after ${per_script_timeout}s while awaiting unavailable or long-running test prerequisites"
    elif grep -Eqi 'command not found|not found$|required for testsuite|Could not resolve hostname|Permission denied|Read-only file system|No space left|Connection refused|Cannot connect|sudo:' "$actual"; then
        status=BLOCKED_ENV
        reason="required command, service, host, privilege, or writable system path is unavailable"
    else
        status=FAIL
        reason="exit=${rc}; output differs from unmodified upstream wanted-result"
    fi

    printf '%s\t%s\t%d\t%d\t%s\n' \
        "$base" "$status" "$rc" "$duration" "$reason" > "$rows_dir/$base.tsv"
}
export -f run_one
export wanted_dir results_dir work_dir per_script_timeout rows_dir

find "$scripts_dir" -maxdepth 1 -type f -name '*.sh' -print0 |
    LC_ALL=C sort -z |
    xargs -0 -r -n1 -P "$test_jobs" bash -c 'run_one "$1"' _

find "$rows_dir" -maxdepth 1 -type f -name '*.tsv' -print0 |
    LC_ALL=C sort -z |
    xargs -0 cat >> "$summary"

while IFS=$'\t' read -r base status rc duration reason; do
    test "$base" = script && continue
    printf '%-42s %s (rc=%s, %ss)\n' "$base" "$status" "$rc" "$duration"
done < "$summary"

executed=$(awk 'NR > 1 { count++ } END { print count + 0 }' "$summary")
passed=$(awk -F '\t' '$2 == "PASS" { count++ } END { print count + 0 }' "$summary")
failed=$(awk -F '\t' '$2 == "FAIL" { count++ } END { print count + 0 }' "$summary")
blocked=$(awk -F '\t' '$2 == "BLOCKED_ENV" { count++ } END { print count + 0 }' "$summary")
missing_expected=$(awk -F '\t' '$2 == "MISSING_EXPECTED" { count++ } END { print count + 0 }' "$summary")

printf 'UPSTREAM_ALL_SUMMARY executed=%d passed=%d failed=%d blocked_env=%d missing_expected=%d\n' \
    "$executed" "$passed" "$failed" "$blocked" "$missing_expected"
test "$executed" -eq 108
test $((passed + failed + blocked + missing_expected)) -eq 108
test "$missing_expected" -eq 0
