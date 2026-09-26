#!/bin/sh
# smoke_test.sh — 3d-ascii-viewer-c 1.4.0 test_package 测试源（L0c 门禁）
#
# 真实调用被测 CLI 的公开行为并断言可观察结果（不是空壳/只打印字符串）：
#   T1: --snap <az> <al> -w -h 渲染捆绑 fox.obj → 输出 ≥10 行非空 ASCII 帧且 rc=0
#   T2: --help 输出使用说明（含 "Usage:" 与 "--snap" 选项）
# 由 test_package/conanfile.py 的 test() 通过 self.run 实际执行（L0d）。
#
# 用法: sh smoke_test.sh <exe> <model> [TERMINFO 目录]
# 退出码: 0=全部断言通过; 1=断言失败; 2=用法/参数错误
set -u
BIN="${1:-}"
MODEL="${2:-}"
TINFO_DIR="${3:-}"

[ -n "$BIN" ] && [ -f "$BIN" ] || { echo "usage: $0 <binary> <model.obj> [terminfo-dir]"; exit 2; }
[ -f "$MODEL" ] || { echo "FAIL: model not found: $MODEL"; exit 2; }

TINFO=""
[ -n "$TINFO_DIR" ] && TINFO="TERMINFO=$TINFO_DIR"

fail=0
chk() { if [ "$2" = "0" ]; then echo "PASS: $1"; else echo "FAIL: $1"; fail=1; fi }

echo "--- 3d-ascii-viewer-c 1.4.0 test_package smoke test ---"

# T1: --snap 渲染 fox.obj 输出非空 ASCII 帧（公开 API: --snap <az> <al> -w -h）
out=$(env TERM=xterm $TINFO "$BIN" --snap 30 20 -w 60 -h 24 "$MODEL" 2>&1); rc=$?
lines=$(echo "$out" | grep -c '[^[:space:]]' 2>/dev/null || echo 0)
if [ "$rc" = "0" ] && [ "$lines" -ge 10 ]; then
    chk "T1 --snap 渲染 fox.obj 输出 ${lines} 行非空帧 (rc=0)" 0
else
    echo "  rc=$rc lines=$lines"
    chk "T1 --snap 渲染 fox.obj" 1
fi

# T2: --help 输出使用说明（含 Usage 与 --snap 选项）
out=$("$BIN" --help 2>&1)
echo "$out" | grep -q "Usage:" && echo "$out" | grep -q -- "--snap" && r=0 || r=1
chk "T2 --help 含 Usage 与 --snap 说明" "$r"

if [ "$fail" = "0" ]; then echo "--- smoke test: ALL PASS ---"; else echo "--- smoke test: FAILED ---"; fi
exit $fail