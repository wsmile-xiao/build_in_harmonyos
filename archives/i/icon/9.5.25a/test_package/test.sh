#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for icon executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[test] icon -V"
icon -V && echo "[ok] icon -V succeeded" || {
    echo "[fail] icon -V failed"
    exit 1
}

echo "[test] icont hello.icn"
echo 'procedure main(); write("Hello from Icon!"); end' > hello.icn
icont hello.icn && ./hello && echo "[ok] icont succeeded" || {
    echo "[fail] icont failed"
    exit 1
}

echo "[test] math operation"
echo 'procedure main(); write(2+3); end' > math.icn
icont math.icn && ./math | grep -q "^5$" && echo "[ok] math succeeded" || {
    echo "[fail] math failed"
    exit 1
}
