#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for aube executable
# Runs in conanrun env (PATH includes installed bin/)
set -eu

echo "[test] aube --version"
aube --version && echo "OK --version" || {
    echo "[test] --version failed, trying --help..."
    aube --help > /dev/null 2>&1 && echo "OK --help" || {
        echo "FAIL aube failed both --version and --help"
        exit 1
    }
}
echo "[test] aube --help"
aube --help > /dev/null && echo "OK --help"
