#!/bin/sh
# consumer_demo.sh — 消费者用例：模拟下游用户的典型工作流。
#
# 场景：版本库管理员（或 cvsweb/viewvc 集成方）拿到 cvsgraph 包后，
# 对一个带侧分支的 RCS 仓库渲染版本树。
#   (1) 分支树 → PNG 图像（cvswrappers/文档生成场景）
#   (2) 同一棵树 → HTML imagemap（cvsweb 集成场景），并断言侧分支
#       版本 1.2.2.1 与主干头 1.3 都出现在 map 输出中
#
# 用法（test_package/conanfile.py 与手工均适用）：
#   CVSGRAPH=<pkg>/bin/cvsgraph sh consumer_demo.sh [输出前缀]
# 输出文件写到可写目录（第一个参数），规避 OHOS 只读 /tmp。
set -e

here=$(dirname "$0")
out="${1:-$PWD/consumer-out}"
CVSGRAPH="${CVSGRAPH:-cvsgraph}"

# (1) branching RCS tree -> PNG
"$CVSGRAPH" -c "$here/cvsgraph.conf" -o "$out-branch.png" -r "" "$here/test-branch.txt,v"
magic=$(head -c 4 "$out-branch.png" | od -An -tx1 | tr -d ' \n')
if [ "$magic" != "89504e47" ]; then
    echo "FAIL: branch tree output is not a PNG (magic=$magic)"
    exit 1
fi

# (2) same tree -> HTML imagemap with branch + trunk-head assertions
"$CVSGRAPH" -c "$here/cvsgraph.conf" -i -M consumer_map -o "$out-branch.map" -r "" "$here/test-branch.txt,v"
grep -q '<map name="consumer_map"' "$out-branch.map" || {
    echo "FAIL: imagemap has no <map> element"; exit 1; }
grep -q 'rev=1.2.2.1' "$out-branch.map" || {
    echo "FAIL: side branch revision 1.2.2.1 missing from imagemap"; exit 1; }
grep -q 'rev=1.3' "$out-branch.map" || {
    echo "FAIL: trunk head revision 1.3 missing from imagemap"; exit 1; }

echo "PASS: consumer demo — branch tree PNG + imagemap (side branch 1.2.2.1, trunk head 1.3)"
