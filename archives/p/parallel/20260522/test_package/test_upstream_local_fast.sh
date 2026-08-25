#!/usr/bin/env bash
set -euo pipefail

parallel_bin=$1
upstream_tests=$2
perl_bin=$3
source_script="$upstream_tests/tests-to-run/parallel-local-fast.sh"
wanted_results="$upstream_tests/wanted-results/parallel-local-fast"

file_count=$(find "$upstream_tests" -type f | wc -l | tr -d ' ')
test "$file_count" -eq 390
printf 'PASS: retained complete upstream testsuite (%d/390 files)\n' "$file_count"

export PARALLEL_SHELL=bash
export LC_ALL=C

work_dir=$(mktemp -d "${TMPDIR:-$HOME}/parallel-upstream.XXXXXX")
trap 'rm -rf "$work_dir"' EXIT
cat > "$work_dir/parallel" <<EOF
#!/usr/bin/env sh
exec "$perl_bin" "$parallel_bin" "\$@"
EOF
chmod +x "$work_dir/parallel"
export PATH="$work_dir:$PATH"

# Load the original upstream functions without executing the suite-wide runner
# at the bottom of parallel-local-fast.sh.
awk '/^export -f / { exit } { print }' "$source_script" > "$work_dir/functions.sh"
# shellcheck source=/dev/null
source "$work_dir/functions.sh"

selected=(
    par_fast_basic
    par_fast_jobs
    par_fast_keeporder
    par_fast_large
    par_fast_multisource
    par_fast_null
    par_fast_perl_expr
    par_fast_replacement_dot
    par_fast_replacement_dotslash
    par_fast_replacement_slash
)

: > "$work_dir/actual"
for test_name in "${selected[@]}"; do
    "$test_name" 2>&1 | sed "s/^/${test_name}\t/" >> "$work_dir/actual"
done

selection_pattern=$(IFS='|'; printf '%s' "${selected[*]}")
awk -F '\t' -v pattern="^(${selection_pattern})$" '$1 ~ pattern' \
    "$wanted_results" > "$work_dir/expected"

diff -u "$work_dir/expected" "$work_dir/actual"
printf 'PASS: %d unmodified upstream parallel-local-fast cases\n' "${#selected[@]}"
