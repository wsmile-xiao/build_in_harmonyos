#!/usr/bin/env bash
# test_harmony_tmpdir.sh — 鸿蒙特有测试：验证 0002-mktemp-tmpdir.patch 的平台适配点。
#
# 背景：鸿蒙沙箱 /tmp 为只读 erofs（E002），上游 mussh 硬编码 TEMP_BASE=/tmp，
# 临时目录创建必败；0002 补丁改为 TEMP_BASE=${TMPDIR:-/tmp}。
# 本测试验证：TMPDIR 指向自定义可写目录时，mussh 主流程 create_temp()
# 创建的临时目录基址落在 $TMPDIR 下（而非硬编码 /tmp）。
#
# 方法：预置 mktemp stub（记录目录模板参数后转调真实 mktemp），
# TMPDIR 指向自定义目录，触发 mussh 主流程（-h localhost -c date，超时兜底，
# 不依赖 sshd），断言 stub 日志中的模板以 $TMPDIR 开头。
set -euo pipefail

MUSSH="$1"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

LOGDIR="$WORK/log"; mkdir -p "$LOGDIR"
STUBDIR="$WORK/stub"; mkdir -p "$STUBDIR"
TMP_BASE="$WORK/tmpbase"; mkdir -p "$TMP_BASE"

# 真实 mktemp 绝对路径（stub 内转调，避免 PATH 前缀导致递归命中自身）
REAL_MKTEMP="$(command -v mktemp)"
export MUSSH_TEST_LOG="$LOGDIR/mktemp.args"
cat > "$STUBDIR/mktemp" <<EOF
#!/usr/bin/env bash
echo "\$@" >> "\$MUSSH_TEST_LOG"
exec "$REAL_MKTEMP" "\$@"
EOF
chmod +x "$STUBDIR/mktemp"

export TMPDIR="$TMP_BASE"
export PATH="$STUBDIR:$PATH"

# 触发 mussh 主流程 create_temp()：无 sshd 时可能秒退或短暂挂起，
# 以后台 + 超时杀兜底（不依赖 timeout 命令）
bash "$MUSSH" -h localhost -c "date" >/dev/null 2>&1 &
PID=$!
sleep 3
kill "$PID" 2>/dev/null || true
wait "$PID" 2>/dev/null || true

if [ ! -s "$MUSSH_TEST_LOG" ]; then
    echo "FAIL: mussh 未调用 mktemp（主流程未走到 create_temp）" >&2
    exit 1
fi
if grep -q "$TMP_BASE/" "$MUSSH_TEST_LOG"; then
    echo "OK: mussh 临时目录基址遵循 TMPDIR（stub 记录: $(head -1 "$MUSSH_TEST_LOG")）"
    exit 0
fi
echo "FAIL: mussh 临时目录基址未遵循 TMPDIR=$TMP_BASE; stub 日志: $(cat "$MUSSH_TEST_LOG")" >&2
exit 1
