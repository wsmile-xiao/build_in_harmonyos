#!/data/service/hnp/bin/bash
# test_package/test.sh — ink 0.5.3 冒烟测试（在 conanrun 环境中运行，PATH 含安装的 bin/）
set -eu

echo "[test] ink -v"
out=$(ink -v)
echo "$out"

# 断言 1：-v 输出首行 = PACKAGE_STRING（ink 0.5.3）
echo "$out" | grep -q '^ink 0\.5\.3$'
# 断言 2：-v 会调用 libinklevel get_version_string()，第二行为 libinklevel 版本串
# （证明 ink 可执行且动态链接 libinklevel 成功）
echo "$out" | grep -q 'libinklevel'

echo "[test] ✅ ink -v OK（二进制可执行 + libinklevel 动态链接验证）"
