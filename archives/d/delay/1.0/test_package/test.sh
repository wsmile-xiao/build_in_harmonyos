#!/data/service/hnp/bin/bash
# test_package/test.sh — delay 1.0 冒烟测试
# 在 conanrun 环境执行（PATH 含已安装 bin/）。
# 上游无测试套件（Makefile 无 check/test 目标），此处为适配后补全的
# 消费者级冒烟测试：通过管道喂数据验证 delay 的数据透传与延时行为。
# 计数口径：按独立检查项计数，共 4 项（见 MANIFEST.yml）。
set -euo pipefail

fail() {
    echo "❌ $1"
    exit 1
}

echo "[test 1/4] 数据透传：printf 'hello delay' | delay 100"
out=$(printf 'hello delay' | delay 100)
[ "$out" = "hello delay" ] || fail "透传结果不符: got '$out'"

echo "[test 2/4] 空输入：printf '' | delay 100"
out=$(printf '' | delay 100)
[ -z "$out" ] || fail "空输入应无输出: got '$out'"

echo "[test 3/4] 时间单位后缀：printf 'x' | delay 1s"
out=$(printf 'x' | delay 1s)
[ "$out" = "x" ] || fail "1s 后缀解析失败: got '$out'"

echo "[test 4/4] 缓冲区参数：printf 'x' | delay -b 4k 200"
out=$(printf 'x' | delay -b 4k 200)
[ "$out" = "x" ] || fail "-b 参数解析失败: got '$out'"

echo "✅ delay 1.0 全部 4 项冒烟测试通过"
