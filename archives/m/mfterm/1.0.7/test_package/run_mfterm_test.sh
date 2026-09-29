#!/bin/sh
# run_mfterm_test.sh — mfterm 消费者冒烟测试（R34/PF3 口径：真实执行安装产物）
#
# 用法: run_mfterm_test.sh <mfterm-binary-path>
#
# 判据（libnfc-tools run_nfc_tools_test.sh 范式）：
#   - exit 0            → OK（命令正常执行）
#   - exit 126/127      → FAIL（动态库加载失败 / 找不到解释器）
#   - 其他非零退出码    → WARN（命令本身报错，如无 NFC 硬件，容忍但提示）
#
# 测试点（全部离线，无需 NFC 硬件；2026-09-20 OHOS aarch64 真机实测回填）：
#   1. --version      参数解析 + 版本字符串输出（期望含 1.0.7）
#   2. --help         参数解析 + 用法输出（readline 链接正常）
#   3. mac key <k0..k7> 载入 Crypto-1 MAC 密钥（term_cmd.c 命令表语法：
#                      8 个空格分隔 hex 字节）
#   4. mac compute 0  对全零块计算 CBC-MAC（DES 核心，算法正确性断言：
#                      全零密钥+全零块 → "8c a6"；全 ff 密钥 → "ca aa"，
#                      两密钥产生不同 MAC 证明密钥真实参与计算）
#   5. quit           优雅退出（stdin 管道关闭时 exit 0）
set -eu

BIN="$1"
[ -f "$BIN" ] || { echo "FAIL: mfterm not found at $BIN"; exit 1; }

fail() { echo "FAIL: $*"; exit 1; }
warn() { echo "WARN: $*"; }

echo "[1/5] mfterm --version"
# 同 [2/5]：先单独捕获真实 rc 再 grep（管道 $? 是 grep 的，且 126/127 的
# shell 错误消息含脚本路径 "1.0.7" 会造成假 ok，必须先过 rc 闸门）
VER_RC=0
VER_OUT=$("$BIN" --version </dev/null 2>&1) || VER_RC=$?
if [ "$VER_RC" = "126" ] || [ "$VER_RC" = "127" ]; then
    fail "mfterm --version load error (rc=$VER_RC)"
fi
if echo "$VER_OUT" | grep -q "1.0.7"; then
    echo "  ok: version string contains 1.0.7"
else
    warn "mfterm --version rc=$VER_RC (no 1.0.7 in output)"
fi

echo "[2/5] mfterm --help"
# 先单独捕获 mfterm 自身退出码再 grep 输出（管道里 $? 是 grep 的，126/127 会被掩盖成 1）
HELP_RC=0
HELP_OUT=$("$BIN" --help </dev/null 2>&1) || HELP_RC=$?
if [ "$HELP_RC" = "126" ] || [ "$HELP_RC" = "127" ]; then
    fail "mfterm --help load error (rc=$HELP_RC)"
fi
if echo "$HELP_OUT" | grep -qi "usage"; then
    echo "  ok: --help prints usage"
else
    warn "mfterm --help rc=$HELP_RC (no usage text)"
fi

# 3/5 + 4/5: 离线命令序列（无 NFC 硬件即可运行）
# 语法见 term_cmd.c 命令表: "mac key <k0..k7>" / "mac compute <block>"
# 期望值 2026-09-20 OHOS aarch64 真机实测（全零密钥 → 8c a6；
# 全 ff 密钥 → ca aa；两值不同证明密钥参与 MAC 计算）
echo "[3/5] mac key (load Crypto-1 key, 8 hex bytes)"
echo "[4/5] mac compute 0 (CBC-MAC, DES core)"
OUT=$(printf 'mac key 00 00 00 00 00 00 00 00\nmac compute 0\nquit\n' | "$BIN" 2>&1) || {
    rc=$?
    if [ "$rc" = "126" ] || [ "$rc" = "127" ]; then
        fail "mfterm offline command load error (rc=$rc)"
    fi
    warn "mfterm mac command rc=$rc"
}
# 确定性算法断言（P2）：全零密钥+全零块的 CBC-MAC 必须等于 8c a6
# （预期值经独立 DES 实现复核：24 字节全零输入 → 8c a6 4d e9 c1 b1 23 a7）
if echo "$OUT" | grep -q "Block 00, MAC : 8c a6"; then
    echo "  ok: MAC of all-zero key+block matches expected 8c a6"
else
    fail "Crypto-1 CBC-MAC mismatch for all-zero key (expected 'Block 00, MAC : 8c a6', got: $(echo "$OUT" | grep 'MAC :' || echo '<no MAC output>'))"
fi
OUT2=$(printf 'mac key ff ff ff ff ff ff ff ff\nmac compute 0\nquit\n' | "$BIN" 2>&1) || warn "second key run rc=$?"
# 确定性算法断言（P2）：全 ff 密钥必须等于 ca aa（与全零密钥结果不同 → 密钥真实参与计算）
if echo "$OUT2" | grep -q "Block 00, MAC : ca aa"; then
    echo "  ok: MAC differs for all-ff key (ca aa) — key participates in MAC"
else
    fail "Crypto-1 CBC-MAC mismatch for all-ff key (expected 'Block 00, MAC : ca aa', got: $(echo "$OUT2" | grep 'MAC :' || echo '<no MAC output>'))"
fi

echo "[5/5] graceful exit on closed stdin"
if printf 'quit\n' | "$BIN" >/dev/null 2>&1; then
    echo "  ok: quit command exits cleanly"
else
    rc=$?
    if [ "$rc" = "126" ] || [ "$rc" = "127" ]; then
        fail "mfterm quit load error (rc=$rc)"
    fi
    warn "mfterm quit rc=$rc"
fi

echo "mfterm consumer smoke test: DONE"
