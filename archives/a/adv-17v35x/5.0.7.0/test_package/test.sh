#!/data/service/hnp/bin/bash
# test_package — 真实消费 adv-17v35x 用户态工具 getconfig
set -eu

echo "[1/3] getconfig 无参数：应打印 Usage 且退出码 1"
set +e
out=$(getconfig 2>&1)
rc=$?
set -e
if [ "$rc" -ne 1 ]; then
    echo "FAIL: 期望退出码 1，实际 $rc"
    exit 1
fi
echo "$out" | grep -q "Usage" || { echo "FAIL: 未输出 Usage"; exit 1; }

echo "[2/3] getconfig ttyA 0：应退出码 0"
getconfig ttyA 0

echo "[3/3] getconfig ttyB 0：应退出码 0"
getconfig ttyB 0

echo "ALL TESTS PASSED"