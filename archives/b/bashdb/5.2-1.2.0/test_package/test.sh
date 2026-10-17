#!/data/service/hnp/bin/bash
# test.sh — 实质验证 bashdb 可执行文件：
#   HarmonyOS 拒绝通过 shebang 直接 exec 脚本文件，因此用 `bash bashdb` 显式执行。
#   1) bashdb --version 输出版本
#   2) 用 bashdb 实际调试一个简单 bash 脚本（非交互：立即退出）
set -e

BASHDB_BIN="$(command -v bashdb)"
if [ -z "$BASHDB_BIN" ]; then
    echo "ERROR: bashdb 不在 PATH 中" >&2
    exit 1
fi

echo "== 1) bashdb --version =="
bash "$BASHDB_BIN" --version

echo
echo "== 2) 用 bashdb 实际调试脚本 =="
DBG_SCRIPT="${TMPDIR:-/tmp}/bashdb_smoke_test.sh"
cat > "$DBG_SCRIPT" <<'EOF'
#!/bin/bash
# simple script to be debugged by bashdb
echo "hello from bashdb smoke test"
x=42
echo "x=$x"
EOF

# 非交互运行 bashdb：进入调试器后立即退出（输入 quit）
if echo "quit" | bash "$BASHDB_BIN" "$DBG_SCRIPT" >/dev/null 2>&1; then
    echo "bashdb 调试会话运行成功"
else
    echo "ERROR: bashdb 调试会话失败" >&2
    exit 1
fi

rm -f "$DBG_SCRIPT"
echo "== bashdb smoke test 全部通过 =="
