#!/bin/sh
# test_ohos — 3d-ascii-viewer-c 1.4.0 HarmonyOS PC 专项验证（自包含，可单独执行）
#
# 在真实鸿蒙 PC（aarch64, OHOS）上对最终 Conan 包做独立专项检查，
# 区别于上游（上游无测试套件，仅有样例模型数据）与 test_package 消费者用例：
#
#   T1  aarch64 ELF 验证（产物为 ELF64 AArch64，可在 OHOS 执行）
#   T2  OHOS 可执行位与宿主路径泄漏检查（无 /storage、/home 等宿主绝对路径）
#   T3  真实渲染路径：TERM/TERMINFO 下 --snap 渲染 fox.obj 输出非空 ASCII 帧
#   T4  二进制格式覆盖：--snap 渲染二进制 STL 模型（shiba-inu-binary.stl）输出非空
#   T5  --help 输出核验（消费者可见的使用说明；上游 output_usage 设计上 exit 1，
#       故只核对输出内容不核对退出码）
#
# 用法：sh run_ohos_test.sh <已安装二进制路径> [TERMINFO 目录] [模型目录]
# 退出码：0=全部通过；非 0=有失败（打印首个错误）。
set -u
BIN="${1:-}"
TERMINFO_DIR="${2:-}"
MODEL_ARG="${3:-}"
[ -n "$BIN" ] || { echo "usage: $0 <binary> [terminfo-dir] [model-dir]"; exit 2; }
[ -f "$BIN" ] || { echo "FAIL: binary not found: $BIN"; exit 2; }

fail=0
chk() { # $1=name $2=result
    if [ "$2" = "0" ]; then echo "PASS: $1"; else echo "FAIL: $1"; fail=1; fi
}

echo "--- 3d-ascii-viewer-c HarmonyOS 专项验证 (binary=$BIN) ---"

# T1: aarch64 ELF
readelf -h "$BIN" 2>/dev/null | grep -q "AArch64" && r=0 || r=1
chk "T1 aarch64 ELF (ELF64 AArch64)" "$r"

# T2: 宿主路径泄漏（构建机 /storage /home 绝对路径不得进入产物）
if strings "$BIN" | grep -qE '/storage/|/home/|/Users/'; then
    echo "  leak: $(strings "$BIN" | grep -E '/storage/|/home/|/Users/' | head -1)"
    chk "T2 无宿主绝对路径泄漏" 1
else
    chk "T2 无宿主绝对路径泄漏" 0
fi

BIN_DIR=$(dirname "$BIN")
# 样例模型：优先显式参数，其次包内 share 目录，最后脚本相邻源码树 models
if [ -n "$MODEL_ARG" ]; then
    MODEL_DIR="$MODEL_ARG"
elif [ -f "$BIN_DIR/../share/3d-ascii-viewer-c/models/fox.obj" ]; then
    MODEL_DIR="$BIN_DIR/../share/3d-ascii-viewer-c/models"
else
    for cand in "$(dirname "$0")/../../models" "$(dirname "$0")/../models" "$(dirname "$0")/models"; do
        [ -f "$cand/fox.obj" ] && MODEL_DIR=$(dirname "$cand/fox.obj") && break
    done
fi
[ -n "${MODEL_DIR:-}" ] || { echo "FAIL: model files not found"; exit 2; }
FOX="$MODEL_DIR/fox.obj"
STL="$MODEL_DIR/shiba-inu-binary.stl"
[ -f "$FOX" ] || { echo "FAIL: fox.obj not found in $MODEL_DIR"; exit 2; }
[ -f "$STL" ] || { echo "FAIL: shiba-inu-binary.stl not found in $MODEL_DIR"; exit 2; }

# T3: OBJ 真实渲染（TERM/TERMINFO，--snap 输出非空 ASCII 帧）
if [ -n "$TERMINFO_DIR" ]; then
    TINFO="TERMINFO=$TERMINFO_DIR"
else
    TINFO=""
fi
out=$(env TERM=xterm $TINFO "$BIN" --snap 30 20 -w 60 -h 24 "$FOX" 2>&1); rc=$?
if [ "$rc" = "0" ] && [ -n "$out" ]; then
    chk "T3 --snap 渲染 fox.obj（exit=0 且输出 $(echo "$out" | wc -l) 行非空帧）" 0
else
    echo "  rc=$rc out=$(echo "$out" | head -2)"
    chk "T3 --snap 渲染 fox.obj" 1
fi

# T4: 二进制 STL 覆盖
out=$(env TERM=xterm $TINFO "$BIN" --snap 20 15 -w 40 -h 16 "$STL" 2>&1); rc=$?
if [ "$rc" = "0" ] && [ -n "$out" ]; then
    chk "T4 --snap 渲染 shiba-inu-binary.stl（exit=0 非空帧）" 0
else
    echo "  rc=$rc out=$(echo "$out" | head -2)"
    chk "T4 --snap 渲染 shiba-inu-binary.stl" 1
fi

# T5: --help 输出核验（上游 output_usage() 设计上 exit(1)，只核对输出内容）
out=$("$BIN" --help 2>&1)
echo "$out" | grep -q "Usage:" && echo "$out" | grep -q "INPUT_FILE" && r=0 || r=1
chk "T5 --help 输出含 Usage/INPUT_FILE" "$r"

echo "--- 3d-ascii-viewer-c OHOS 专项: $([ $fail = 0 ] && echo ALL PASS || echo FAILED) ---"
exit $fail