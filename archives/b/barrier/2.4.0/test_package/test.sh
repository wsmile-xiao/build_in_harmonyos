#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for barrier (CLI client)
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

# NOTE: `barriers --version` / `barrierc --version` print the version text but
# intentionally exit(3) (kExitArgs) — barrier's upstream behaviour, not an OHOS
# defect.  So assert on the OUTPUT, never on the exit code.
out="$(report=0; barriers --version || report=$?; exit $report)" 2>&1 || true
echo "==== barriers --version ===="
echo "$out"
echo "$out" | grep -q "Protocol version" && echo "✅ barriers --version OK" || {
    echo "❌ barriers --version did not print version"
    exit 1
}

# barrierc is the client CLI; also verify it executes and prints its usage/version.
cout="$(report=0; barrierc --version || report=$?; exit $report)" 2>&1 || true
echo "==== barrierc --version ===="
echo "$cout"
echo "$cout" | grep -q "Protocol version" && echo "✅ barrierc --version OK" || {
    echo "❌ barrierc --version did not print version"
    exit 1
}

echo "✅ barrier smoke test passed"
