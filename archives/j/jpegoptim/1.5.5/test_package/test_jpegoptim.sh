#!/bin/sh
# test_jpegoptim.sh — 消费者测试：真实运行 jpegoptim 并断言行为
# 用法: test_jpegoptim.sh <jpegoptim_bin> <test_jpg>
#
# 断言:
# 1. --version 输出包含 jpegoptim
# 2. 处理真实 JPEG 文件（解析成功、输出尺寸信息、exit 0）
# 3. -m90 质量上限重压缩模式执行（exit 0）

set -eu

BIN="$1"
TEST_JPG="$2"

# Test 1: version output
VERSION_OUTPUT=$("$BIN" --version 2>&1)
echo "$VERSION_OUTPUT" | grep -q "jpegoptim" || { echo "FAIL: version output missing"; exit 1; }
echo "PASS: version output"

# Test 2: process a real JPEG file (parse + report dimensions)
INFO_OUTPUT=$("$BIN" "$TEST_JPG" 2>&1)
echo "$INFO_OUTPUT" | grep -q "test.jpg" || { echo "FAIL: processing output missing filename: $INFO_OUTPUT"; exit 1; }
echo "$INFO_OUTPUT" | grep -qE "1[ x]+x[ x]*1|1x1" || { echo "FAIL: dimensions not reported: $INFO_OUTPUT"; exit 1; }
echo "PASS: JPEG processing ($INFO_OUTPUT)"

# Test 3: max-quality recompression mode
OPT_OUTPUT=$("$BIN" -m90 "$TEST_JPG" 2>&1)
echo "$OPT_OUTPUT" | grep -q "test.jpg" || { echo "FAIL: optimize run output missing: $OPT_OUTPUT"; exit 1; }
echo "PASS: -m90 recompression mode"

echo "All tests passed."
