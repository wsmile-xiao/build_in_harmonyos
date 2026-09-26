#!/data/service/hnp/bin/bash
# test_package/test.sh — 消费者冒烟测试 for thc (address6 IPv6 离线解析)
# 运行于 conanrun 环境（PATH 已含已安装 bin/，LD_LIBRARY_PATH 已含依赖 .so）。
# 真实运行 address6 二进制（R34），非字符串打印桩。
#
# 重要：thc 的 address6 在「成功解码」时返回正整数（MAC 解码返回 1），仅在
# 「地址不含可解码的 MAC/IPv4」时返回 -1（shell 退出码 255）。故本测试以
# 解码输出内容为准，不依赖退出码 == 0。
set -uo pipefail

BIN=address6
PASS=0
FAIL=0

check() {
  # $1 = 描述, $2 = 实际输出, $3 = 期望输出
  local desc="$1" actual="$2" expect="$3"
  if [ "$actual" = "$expect" ]; then
    echo "PASS: $desc"
    PASS=$((PASS + 1))
  else
    echo "FAIL: $desc (got: '$actual', expected: '$expect')"
    FAIL=$((FAIL + 1))
  fi
}

# --- A1: EUI-64 编码的 MAC 解码（fe80::0211:22ff:fe33:4455 -> 00:11:22:33:44:55）---
OUT1=$( "$BIN" "fe80::0211:22ff:fe33:4455" 2>/dev/null ) || true
check "address6 fe80::0211:22ff:fe33:4455 解码 MAC" "$OUT1" "00:11:22:33:44:55"

# --- A2: 另一个 EUI-64 地址（覆盖不同 MAC，验证非偶然）---
OUT2=$( "$BIN" "fe80::aabb:ccff:fedd:eeff" 2>/dev/null ) || true
check "address6 fe80::aabb:ccff:fedd:eeff 解码 MAC" "$OUT2" "a8:bb:cc:dd:ee:ff"

# --- A3: 错误路径健全性（地址不含可解码的 MAC/IPv4 -> stderr 报 Error）---
ERR3=$( "$BIN" "2001:db8::1" 2>&1 >/dev/null ) || true
if echo "$ERR3" | grep -q "Error:"; then
  echo "PASS: address6 2001:db8::1 正确进入错误路径（无解码，证明是真实二进制）"
  PASS=$((PASS + 1))
else
  echo "FAIL: address6 2001:db8::1 未报告 Error（异常）"
  FAIL=$((FAIL + 1))
fi

echo ""
echo "==== thc 消费者冒烟测试：PASS=$PASS FAIL=$FAIL ===="
[ "$FAIL" -eq 0 ]
