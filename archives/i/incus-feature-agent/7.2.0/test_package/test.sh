#!/data/service/hnp/bin/bash
# test_package/test.sh — incus-feature-agent 安装产物冒烟测试（消费者视角）
set -eu

BIN_DIR="${1:-.}"
BIN="${BIN_DIR}/incus-agent"

echo "[test] incus-agent --version"
"$BIN" --version | grep -qx "7.2" && echo "OK incus-agent --version == 7.2" || {
    echo "FAIL incus-agent --version"; exit 1;
}

echo "[test] incus-agent --help"
"$BIN" --help >/dev/null 2>&1 && echo "OK incus-agent --help" || {
    echo "FAIL incus-agent --help"; exit 1;
}

echo "smoke test PASSED"
