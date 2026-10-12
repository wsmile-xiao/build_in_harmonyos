#!/data/service/hnp/bin/bash
# test_package/test.sh — incus-user 安装产物冒烟测试（消费者视角）
set -eu

BIN_DIR="${1:-.}"
BIN="${BIN_DIR}/incus-user"

echo "[test] incus-user --version"
"$BIN" --version | grep -qx "7.0.1" && echo "OK incus-user --version == 7.0.1" || {
    echo "FAIL incus-user --version"; exit 1;
}

echo "[test] incus-user --help"
"$BIN" --help >/dev/null 2>&1 && echo "OK incus-user --help" || {
    echo "FAIL incus-user --help"; exit 1;
}

echo "smoke test PASSED"
