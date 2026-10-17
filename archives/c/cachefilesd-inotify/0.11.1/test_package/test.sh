#!/data/service/hnp/bin/bash
# test_package/test.sh — cachefilesd-inotify 冒烟测试
# 在 conanrun env 中运行（PATH 含已安装的 bin/，cachefilesd 可直接调用）
set -eu

echo "[test] cachefilesd --version"
out=$(cachefilesd --version)
echo "$out"

echo "[test] 校验版本号 0.11.1"
echo "$out" | grep -q "0.11.1" || {
    echo "❌ 版本号不匹配，期望含 0.11.1"
    exit 1
}

echo "✅ cachefilesd --version OK (0.11.1)"
