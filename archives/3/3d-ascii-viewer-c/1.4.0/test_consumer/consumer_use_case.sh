#!/bin/sh
# consumer_use_case — 3d-ascii-viewer-c 1.4.0 消费者用例
#
# 消费者用例语义：模拟业务上层组件/应用，仅通过库已安装/导出的公开接口
# （CLI 运行时产物 `3d-ascii-viewer` 的公开命令行选项 --snap/--help/--color）
# 使用该三方库，验证第三方使用者能够调用并得到可观察结果。
# 本库为 CLI 应用（无库头文件/链接目标），公开 API = 命令行接口与其样例行
# 为；不包含库私有头、不调用内部符号、不复用内部测试构建目录。
#
# 用例场景：上层应用（如终端 3D 预览组件）调用 3d-ascii-viewer 将
# models/fox.obj 渲染为 ASCII 帧并展示给用户。
#
# 用法：sh consumer_use_case.sh <已安装二进制路径> <模型目录> [TERMINFO 目录]
# 退出码：0=全部通过；非 0=失败。
set -u
BIN="${1:-}"
MODELS="${2:-}"
TERMINFO_DIR="${3:-}"
[ -n "$BIN" ] && [ -f "$BIN" ] || { echo "usage: $0 <binary> <models-dir> [terminfo-dir]"; exit 2; }
[ -d "$MODELS" ] || { echo "FAIL: models dir not found: $MODELS"; exit 2; }

fail=0
chk() { if [ "$2" = "0" ]; then echo "PASS: $1"; else echo "FAIL: $1"; fail=1; fi }

echo "--- 消费者用例 (3d-ascii-viewer-c 1.4.0) ---"

if [ -n "$TERMINFO_DIR" ]; then TINFO="TERMINFO=$TERMINFO_DIR"; else TINFO=""; fi

# C1: 业务快照渲染（公开 API: --snap <az> <al> + -w/-h 尺寸）→ 输出非空 ASCII 帧
out=$(env TERM=xterm $TINFO "$BIN" --snap 30 20 -w 60 -h 24 "$MODELS/fox.obj" 2>&1); rc=$?
lines=$(echo "$out" | grep -c '[^[:space:]]' 2>/dev/null || echo 0)
if [ "$rc" = "0" ] && [ "$lines" -ge 10 ]; then
    chk "C1 --snap 渲染 fox.obj 输出 ${lines} 行非空帧 (rc=0)" 0
else
    echo "  rc=$rc lines=$lines"
    chk "C1 --snap 渲染 fox.obj" 1
fi

# C2: 使用帮助接口（公开 API: --help）获得使用说明
out=$("$BIN" --help 2>&1)
echo "$out" | grep -q "Usage:" && echo "$out" | grep -q -- "--snap" && r=0 || r=1
chk "C2 --help 含 Usage 与 --snap 说明" "$r"

# C3: 直接调用退出码契约：非法文件报错（非 0）
"$BIN" --snap 10 10 "$MODELS/nonexistent.obj" >/dev/null 2>&1; rc=$?
[ "$rc" != "0" ] && r=0 || r=1
chk "C3 非法模型文件返回非 0（rc=$rc）" "$r"

echo "--- 消费者用例: $([ $fail = 0 ] && echo ALL PASS || echo FAILED) ---"
exit $fail