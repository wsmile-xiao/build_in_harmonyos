#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer smoke test for the robodoc executable.
# Runs inside the conanrun environment, so the packaged bin/ is on PATH.
# R34: genuinely exercises the packaged binaries.
set -euo pipefail

work="$(mktemp -d "${TMPDIR:-/tmp}/robodoc-smoke-XXXXXX")"
trap 'rm -rf "${work}"' EXIT

echo "[step] robodoc --version"
version="$(robodoc --version)"
echo "        robodoc reports: ${version}"
[ "${version}" = "4.99.44" ] || {
    echo "        [fail] expected version 4.99.44, got '${version}'"
    exit 1
}

echo "[step] robodoc --help"
robodoc --help > "${work}/robodoc-help.out" 2>&1 || true
grep -q "ROBODoc Version 4.99.44" "${work}/robodoc-help.out" || {
    echo "        [fail] robodoc --help did not print the version banner"
    exit 1
}

echo "[step] robohdrs runs"
# robohdrs prints its banner to stderr and exits non-zero without arguments,
# so capture the output and ignore the exit status (pipefail would otherwise
# mask a successful grep).
robohdrs > "${work}/robohdrs.out" 2>&1 || true
grep -q "robodoc header insertor" "${work}/robohdrs.out" || {
    echo "        [fail] robohdrs did not print its banner"
    exit 1
}

echo "        [ok] robodoc/robohdrs binaries are functional"
