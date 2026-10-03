#!/bin/bash
# test_consumer/consumer_use_case.sh — vmime 0.9.2 消费者端到端用例
#
# 模拟上层业务组件，仅通过已安装的 conan 包公开 API（find_package(vmime)）
# 使用 vmime 库，不包含任何库内部符号或内部构建目录引用。
#
# 用例场景：上层应用（如邮件客户端组件）构造含附件的 MIME 消息、
#          序列化写入文件，再从磁盘读取解析并提取附件内容。
#
#   C1  构造含二进制附件的 MIME 消息 → 序列化 → 写入 TMPDIR 文件
#   C2  从文件重解析，核对发件人/主题
#   C3  提取附件，核对文件名与内容逐字节一致
#
# 用法：
#     sh consumer_use_case.sh [work-dir]
#   （vmime/0.9.2 从本机 conan cache 解析，需先完成 conan create）
#
# 退出码：0=全部通过；非 0=失败。

set -u

WORK_DIR_ARG="${1:-}"

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HERE/../../../../.." && pwd)"
PROFILE="$REPO_ROOT/ci/conan/profiles/ohos-aarch64"
export PATH="$HOME/usr/local/bin:$PATH"

TMPDIR="${TMPDIR:-$HOME/tmp}"
mkdir -p "$TMPDIR"
export TMPDIR

# Create temp work dir
if [ -n "$WORK_DIR_ARG" ]; then
	WORK_DIR="$WORK_DIR_ARG"
else
	WORK_DIR="$TMPDIR/vmime-consumer-$$"
fi
rm -rf "$WORK_DIR"
mkdir -p "$WORK_DIR"

echo "=== vmime 0.9.2 consumer E2E test ==="
echo "workdir: $WORK_DIR"

# Build consumer project via conan install
cp "$HERE/consumer_vmime.cpp" "$WORK_DIR/"
cp "$HERE/CMakeLists.txt" "$WORK_DIR/"
cp "$HERE/conanfile.txt" "$WORK_DIR/"

cd "$WORK_DIR" || { echo "FAIL: cannot cd $WORK_DIR"; exit 1; }

echo "[1/4] conan install for consumer..."
if ! conan install "$WORK_DIR" \
	-pr:h="$PROFILE" -pr:b="$PROFILE" \
	-of "$WORK_DIR" 2>&1 | tail -5; then
	echo "FAIL: conan install for consumer failed"
	exit 1
fi

echo "[2/4] cmake configure..."
if ! cmake -S "$WORK_DIR" -B "$WORK_DIR/build" \
	-DCMAKE_TOOLCHAIN_FILE="$WORK_DIR/conan_toolchain.cmake" \
	-DCMAKE_BUILD_TYPE=Release 2>&1 | tail -5; then
	echo "FAIL: cmake configure for consumer failed"
	exit 1
fi

echo "[3/4] cmake build..."
if ! cmake --build "$WORK_DIR/build" -- -j4 2>&1 | tail -5; then
	echo "FAIL: cmake build for consumer failed"
	exit 1
fi

echo "[4/4] run consumer..."
CONSUMER_BIN="$WORK_DIR/build/consumer_vmime"
if [ ! -f "$CONSUMER_BIN" ]; then
	echo "FAIL: consumer binary not found at $CONSUMER_BIN"
	exit 1
fi

if "$CONSUMER_BIN"; then
	echo "=== CONSUMER_USE_CASE_ALL_PASS ==="
	exit 0
else
	echo "FAIL: consumer returned non-zero"
	exit 1
fi