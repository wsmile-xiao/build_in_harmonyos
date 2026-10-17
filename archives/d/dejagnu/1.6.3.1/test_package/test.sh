#!/data/service/hnp/bin/bash
# test_package/test.sh -- smoke test for the dejagnu runtest script
# Runs in conanrun env (PATH includes the installed bin/).
# R34: genuinely exercises the packaged runtest tool.
set -euo pipefail

echo "[step] runtest version check"
runtest --version > runtest-output.txt 2>&1 || true

grep -q "DejaGnu version" runtest-output.txt || {
    echo "        [fail] runtest did not print DejaGnu version string"
    cat runtest-output.txt
    exit 1
}

echo "        [ok] runtest is functional"

# Verify the dejagnu report-card tool is also present
dejagnu --version > dejagnu-output.txt 2>&1 || true
grep -q "DejaGnu" dejagnu-output.txt || {
    echo "        [fail] dejagnu script did not print expected version string"
    cat dejagnu-output.txt
    exit 1
}

echo "        [ok] dejagnu smoke test passed"
