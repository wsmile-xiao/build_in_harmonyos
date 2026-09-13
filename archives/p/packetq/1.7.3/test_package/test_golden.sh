#!/bin/sh
# test_golden.sh — packetq 1.7.3 消费者金标测试（L0c 测试源文件）
# 由 test_package/conanfile.py 调用，$1 = 已安装 packetq 二进制，
# $2 = sample.pcap.b64（金标 pcap 的 base64 文本形式——二进制进不了
# GitCode PR diff（checkout-pr git apply 无法应用二进制补丁，PR #9118
# 实测），故以文本形态入库、测试时解码还原）。
# 三断言：版本横幅、金标行数（上游 sample.pcap 恰含 8 个 DNS 包）、
# qname 聚合含 www.se.（上游样本中 www.se. 解析两次）。
set -eu

bin="$1"
b64="$2"
[ -x "$bin" ] || { echo "FAIL: $bin 不存在或不可执行"; exit 1; }
[ -f "$b64" ] || { echo "FAIL: $b64 不存在"; exit 1; }

pcap="${TMPDIR:-/tmp}/packetq-test-$$.pcap"
trap 'rm -f "$pcap"' EXIT
base64 -d < "$b64" > "$pcap" 2>/dev/null \
  || base64 -D -i "$b64" -o "$pcap" \
  || { echo "FAIL: base64 解码 $b64 失败"; exit 1; }

# 1. 版本横幅
ver=$("$bin" --version 2>&1) || { echo "FAIL: packetq --version 退出码非零"; exit 1; }
echo "$ver" | grep -q "1.7.3" || { echo "FAIL: 版本横幅不含 1.7.3: $ver"; exit 1; }

# 2. 金标行数：count(*) 必须为 [8]（经 brew packetq macOS 交叉验证）
cnt=$("$bin" -s "select count(*) as n from dns;" "$pcap" 2>&1) \
  || { echo "FAIL: count 查询退出码非零"; exit 1; }
echo "$cnt" | tr -d ' ' | grep -q '\[8\]' \
  || { echo "FAIL: dns 行数不是 [8]: $cnt"; exit 1; }

# 3. qname 聚合含 www.se.
qn=$("$bin" -s "select qname, count(*) as n from dns group by qname" "$pcap" 2>&1) \
  || { echo "FAIL: qname 聚合查询退出码非零"; exit 1; }
echo "$qn" | grep -q "www\.se\." \
  || { echo "FAIL: qname 聚合缺 www.se.: $qn"; exit 1; }

echo "packetq tool consumer test PASSED"
