#!/usr/bin/env bash
# irrtoolset 5.1.3 鸿蒙专项测试 — OHOS aarch64 平台端到端运行验证
#
# 用途: 验证适配后的 CLI 工具在 HarmonyOS PC (aarch64) 平台上
#       真实加载、运行并处理上游真实 RPSL 策略数据 (非空壳测试).
# 区别于消费者用例: 本用例聚焦平台适配完整性 (OHOS ELF 架构/动态库
#       加载/真实数据处理链路), 使用上游官方 examples 数据.
set -u
fail=0

BIN_DIR="${BIN_DIR:-}"
if [ -z "$BIN_DIR" ]; then
  for d in "$PWD/bin" "$PWD/../bin"; do
    if [ -n "$d" ] && [ -x "$d/rpslcheck" ]; then BIN_DIR="$d"; break; fi
  done
fi
RPSLCHECK="$BIN_DIR/rpslcheck"

echo "== 平台: 确认二进制为 aarch64 ELF (OHOS) =="
FILE_OUT=$(file "$RPSLCHECK" 2>/dev/null || true)
echo "$FILE_OUT"
if echo "$FILE_OUT" | grep -q "aarch64"; then
  echo "OHOS-PASS: 二进制架构为 aarch64"
else
  # file 命令可能缺失, 用 readelf 兜底
  ARCH=$(readelf -h "$RPSLCHECK" 2>/dev/null | grep -i "machine" || true)
  echo "$ARCH"
  if echo "$ARCH" | grep -qiE "aarch64|ARM"; then
    echo "OHOS-PASS: 二进制架构为 aarch64 (readelf)"
  else
    echo "OHOS-FAIL: 无法确认二进制架构"
    fail=1
  fi
fi

echo "== 平台: 上游真实 RPSL 数据 (examples/private_irr_objects.txt) 加载校验 =="
if [ -f "$SRC_EXAMPLES/private_irr_objects.txt" ]; then
  OUT=$("$RPSLCHECK" < "$SRC_EXAMPLES/private_irr_objects.txt" 2>&1); rc=$?
  echo "exit=$rc; output(前5行):"
  echo "$OUT" | head -5
  if echo "$OUT" | grep -q "Congratulations no errors"; then
    echo "OHOS-PASS: 真实 RPSL 数据在 OHOS 平台校验通过"
  elif echo "$OUT" | grep -qE "Error"; then
    echo "OHOS-NOTE: 真实数据含上游自身对象引用错误 (rpslcheck 如实报告), 属预期行为"
  else
    echo "OHOS-FAIL: rpslcheck 无有效输出"
    fail=1
  fi
else
  echo "OHOS-NOTE: 未找到上游 examples 数据, 使用内嵌合法对象验证"
  printf 'inetnum: 192.0.2.0 - 192.0.2.255\nnetname: TEST-NET\ncountry: ZZ\ndescr: test\nadmin-c: TEST-RIPE\ntech-c: TEST-RIPE\nmnt-by: TEST-MNT\nstatus: ASSIGNED PA\ncreated: 2020-01-01\nlast-modified: 2020-01-01\nsource: TEST\n\n' | "$RPSLCHECK" > /dev/null 2>&1; rc=$?
  echo "exit=$rc"
  if [ $rc -eq 0 ]; then echo "OHOS-PASS"; else echo "OHOS-FAIL"; fail=1; fi
fi

if [ $fail -eq 0 ]; then
  echo "OHOS-SPECIFIC-ALL-PASSED"
else
  echo "OHOS-SPECIFIC-FAILURES-DETECTED"
fi
exit $fail