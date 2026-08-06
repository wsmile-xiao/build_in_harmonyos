#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for gcalcli executable
# Runs in conanrun env (PATH includes installed bin/, PYTHONPATH includes deps)
set -eu

echo "[test] gcalcli import test"
python3 -c "import gcalcli; print(f'gcalcli version: {gcalcli.__version__}')" && echo "✅ import OK" || {
    echo "❌ import gcalcli failed"
    exit 1
}
