#!/data/service/hnp/bin/bash
set -euo pipefail

command -v bash_unit >/dev/null
bash_unit -v >/dev/null

workdir="${TMPDIR:-/tmp}/bash-unit-consumer-$$"
mkdir -p "$workdir"
trap 'rm -rf "$workdir"' EXIT

cat > "$workdir/test_sample.sh" <<'EOF'
#!/data/service/hnp/bin/bash

test_bash_unit_is_executable() {
  assert "test -x \"$(command -v bash_unit)\""
}

test_bash_unit_runs_a_real_test() {
  assert_equals "ok" "ok"
}
EOF

if ! output="$(bash_unit "$workdir/test_sample.sh")"; then
  printf '%s\n' "$output" >&2
  exit 1
fi
case "$output" in
  *"Overall result: SUCCESS"*) ;;
  *)
    printf '%s\n' "$output" >&2
    exit 1
    ;;
esac
printf '%s\n' "bash_unit consumer test passed"
