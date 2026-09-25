#!/data/service/hnp/bin/bash
# test_package/test.sh — potool 0.19 消费者测试（R34: 真跑被测二进制）
# 运行于 conanrun 环境（PATH 含被测包 bin/，LD_LIBRARY_PATH 含 glib）
#
# 断言共 5 条（见 MANIFEST.yml assertion_count）：
#   A1 potool -h 用法输出与退出码
#   A2 potool -f t 对上游 fixture 的输出与上游 golden 逐字节一致
#   A3 potool -s 统计输出与上游期望值一致
#   A4 四个辅助脚本随包安装且可执行
#   A5 【鸿蒙适配特有】poedit shebang 为可移植 #!/usr/bin/env bash（补丁已进产物）
set -eu

echo "[A1] potool -h"
HELP_OUT=$(potool -h 2>&1) || { echo "FAIL: potool -h rc!=0"; exit 1; }
echo "$HELP_OUT" | grep -q "Usage:.*FILENAME1" || { echo "FAIL: -h 输出无 Usage 行"; exit 1; }
echo "$HELP_OUT" | grep -q -- "-s.*-c.*-p.*-h" || { echo "FAIL: -h 输出缺过滤/统计选项"; exit 1; }
echo "OK: potool -h rc=0 且含 Usage 与选项说明"

echo "[A2] potool -f t fixtures/in.po → 与上游 golden 逐字节比对"
# 用进程替换直接比对，不落任何中间产物（避免污染提交面）
if ! diff -u fixtures/expected-filter-t.po <(potool -f t fixtures/in.po); then
    echo "FAIL: 过滤输出与上游 golden 不一致"
    exit 1
fi
echo "OK: 与上游 tests/1/f t.po 逐字节一致（$(wc -c < fixtures/expected-filter-t.po) bytes）"

echo "[A3] potool -s 统计"
STATS=$(potool -s fixtures/in.po)
[ "$STATS" = "9" ] || { echo "FAIL: 期望统计 9，实得 '$STATS'"; exit 1; }
echo "OK: potool -s = $STATS"

echo "[A4] 辅助脚本随包安装"
for helper in poedit postats poupdate change-po-charset; do
    p="$(command -v "$helper")" || { echo "FAIL: $helper 不在 PATH"; exit 1; }
    [ -x "$p" ] || { echo "FAIL: $helper 不可执行: $p"; exit 1; }
    echo "OK: $helper -> $p"
done

echo "[A5] 【鸿蒙适配特有】可移植 shebang 已进产物"
SHEBANG=$(head -1 "$(command -v poedit)")
[ "$SHEBANG" = "#!/usr/bin/env bash" ] || {
    echo "FAIL: poedit shebang 期望 '#!/usr/bin/env bash'，实得 '$SHEBANG'"
    exit 1
}
CSHEBANG=$(head -1 "$(command -v change-po-charset)")
[ "$CSHEBANG" = "#!/usr/bin/env perl" ] || {
    echo "FAIL: change-po-charset shebang 期望 '#!/usr/bin/env perl'，实得 '$CSHEBANG'"
    exit 1
}
echo "OK: poedit=#!/usr/bin/env bash, change-po-charset=#!/usr/bin/env perl"

echo "ALL OK: potool 0.19 test_package 5/5 断言通过"
