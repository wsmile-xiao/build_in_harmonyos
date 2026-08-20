#!/system/bin/sh
# test_package/test.sh — smoke test for argo executable
# Runs in conanrun env (PATH includes installed bin/)
# pipefail not supported by /system/bin/sh (mksh) on OHOS
set -eu

echo "[test] argo version"
argo version && echo "PASS: version OK" || {
    echo "[test] version failed, trying help..."
    argo help > /dev/null 2>&1 && echo "PASS: help OK" || {
        echo "FAIL: argo failed both version and help"
        exit 1
    }
}
