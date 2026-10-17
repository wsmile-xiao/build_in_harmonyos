#!/data/service/hnp/bin/bash
# Functional package test: exercise the installed CLI, not source-tree files.
set -eu

scratch_root="${TMPDIR:-${HOME}/tmp}"
test_dir="${scratch_root}/btag-test-$$"
mkdir -p "${test_dir}/empty-library"
trap 'rm -rf "${test_dir}"' EXIT

echo "[test] btag --help"
btag --help > "${test_dir}/help.txt"
grep -q "Usage:" "${test_dir}/help.txt"

echo "[test] btag --dry-run empty directory"
btag --dry-run "${test_dir}/empty-library" > "${test_dir}/dry-run.txt"
grep -q "All done" "${test_dir}/dry-run.txt"

echo "btag package test: 2/2 checks passed"
