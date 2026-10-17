#!/data/service/hnp/bin/bash
# test_package/test.sh — sexpp-cli 0.9.2 消费者测试
# 在 conanrun 环境执行（PATH 含被测包安装出的 bin/）；R34 真实消费被测产物。
set -eu

echo "[test] 1/3 sexpp -h 帮助输出"
sexpp -h | grep -q "S-expressions" || { echo "FAIL: help 输出不含 S-expressions"; exit 1; }
echo "PASS 1: -h 打印帮助"

echo "[test] 2/3 canonical 解析回打（数字 token 须带引号，sexpp 语法）"
OUT=$(printf '(hello (world "42"))' | sexpp -c)
[ "$OUT" = '(5:hello(5:world2:42))' ] || { echo "FAIL: canonical 输出 [$OUT]"; exit 1; }
echo "PASS 2: canonical -> $OUT"

echo "[test] 3/3 advanced transport 回打"
OUT2=$(printf '(hello (world "42"))' | sexpp -a)
[ "$OUT2" = '(hello (world "42"))' ] || { echo "FAIL: advanced 输出 [$OUT2]"; exit 1; }
echo "PASS 3: advanced -> $OUT2"

echo "test sexpp-cli 0.9.2: 3/3 checks PASS"
exit 0
