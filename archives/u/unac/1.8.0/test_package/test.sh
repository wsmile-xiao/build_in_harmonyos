#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for unaccent binary
# Runs in conanrun env (PATH includes installed bin/)
# R34: 实际执行 unaccent 二进制，验证去重音功能（非空壳测试）
set -eu

echo "[test] unaccent UTF-8 café → cafe"
result=$(unaccent UTF-8 "café")
if [ "$result" = "cafe" ]; then
    echo "✅ 去重音测试通过: café → $result"
else
    echo "❌ 去重音测试失败: 期望 'cafe', 得到 '$result'"
    exit 1
fi

echo "[test] unaccent UTF-8 été → ete"
result=$(unaccent UTF-8 "été")
if [ "$result" = "ete" ]; then
    echo "✅ 去重音测试通过: été → $result"
else
    echo "❌ 去重音测试失败: 期望 'ete', 得到 '$result'"
    exit 1
fi

echo "[test] unaccent 版本信息"
output=$(unaccent 2>&1 || true)
if echo "$output" | grep -q "1.8.0"; then
    echo "✅ 版本信息正确: 1.8.0"
else
    echo "❌ 版本信息缺失或错误"
    exit 1
fi

echo "所有测试通过 ✅"
