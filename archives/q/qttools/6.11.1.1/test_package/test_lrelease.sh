#!/bin/sh
# test_lrelease.sh — qttools 6.11.1 L0c 测试源文件
# 实际调用 lrelease 将测试 TS 转换为 QM，验证 Linguist 工具链功能正常
# 用法: test_lrelease.sh <qttools_prefix> <work_dir>
# 退出码: 0=成功, 非0=失败
# POSIX sh 没有可移植的 pipefail；脚本不使用管道来避免吞掉错误。
set -eu

QTTOOLS_PREFIX="${1:-}"
WORK_DIR="${2:-}"

if [ -z "$QTTOOLS_PREFIX" ] || [ -z "$WORK_DIR" ]; then
    echo "FAIL: 用法: test_lrelease.sh <qttools_prefix> <work_dir>" >&2
    exit 1
fi

LRELEASE="$QTTOOLS_PREFIX/bin/lrelease"
if [ ! -x "$LRELEASE" ]; then
    echo "FAIL: lrelease 不存在或不可执行: $LRELEASE" >&2
    exit 2
fi

TS_FILE="$WORK_DIR/test_hello.ts"
QM_FILE="$WORK_DIR/test_hello.qm"

# 写入测试 TS 文件（含中文翻译）
cat > "$TS_FILE" <<'TS_EOF'
<?xml version="1.0" encoding="utf-8"?>
<TS version="2.1" language="zh_CN">
  <context>
    <name>TestContext</name>
    <message>
      <source>Hello</source>
      <translation>你好</translation>
    </message>
  </context>
</TS>
TS_EOF

# 调用 lrelease 转换 TS -> QM
"$LRELEASE" "$TS_FILE" -qm "$QM_FILE"

# 断言 1: QM 文件已生成
if [ ! -f "$QM_FILE" ]; then
    echo "FAIL: lrelease 未生成 QM 文件: $QM_FILE" >&2
    exit 3
fi

# 断言 2: QM 文件非空
QM_SIZE=$(wc -c < "$QM_FILE")
if [ "$QM_SIZE" -le 0 ]; then
    echo "FAIL: 生成的 QM 文件为空: $QM_FILE" >&2
    exit 4
fi

echo "PASS: lrelease test passed — $QM_FILE ($QM_SIZE bytes)"
exit 0
