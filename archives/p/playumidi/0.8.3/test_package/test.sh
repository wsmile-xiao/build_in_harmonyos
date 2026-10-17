#!/data/service/hnp/bin/bash
# test_package/test.sh — playumidi 消费者冒烟测试
# 在 conanrun 环境下执行（PATH 已包含安装后的 bin/）。
# 实质依赖被测包：直接运行 playumidi 可执行文件并校验其真实行为。
#
# 注意 1：本脚本不得在仓库内写任何文件（JC junk gate），全部输出走 stdout 由 conan 捕获；
#         测试用的 MIDI 样例生成到 $TMPDIR 下的工作目录。
# 注意 2：SMF 样例以**文本转义序列内联生成**，不在 PR/仓库中引入二进制文件——
#         平台的 pull/<N>.diff 端点不携带二进制 patch 数据（missing binary patch data），
#         会使 CI 的 checkout-pr 步骤无法应用 diff（实测 #66143 / #66146 两次失败）。
#
# shell 安全模式：使用 -u（未定义变量报错）与 pipefail（管道失败传播）。
# 刻意**不使用 -e**：本脚本需聚合全部用例结果后统一判定（首个用例失败不应中断后续用例），
# 所有失败通过 fail 计数与最终非零退出码显式上报。
set -uo pipefail

WORK="${TMPDIR:-$HOME/tmp}/playumidi-test"
rm -rf "$WORK"; mkdir -p "$WORK"
MID="$WORK/t_min.mid"

# ── SMF (Standard MIDI File) format 0 最小样例，共 71 字节 ──
# MThd | len=6 | fmt=0 | ntrks=1 | division=96
# MTrk | len=0x31 | Δ=0 Meta(track name "PlayuMIDI Consumer Test")
#                 | Δ=0 Meta(tempo 500000) | Δ=0 ProgChange ch0→0
#                 | Δ=0 NoteOn C4 vel100 | Δ=96 NoteOff C4 | Δ=0 Meta(end of track)
printf '\x4d\x54\x68\x64\x00\x00\x00\x06\x00\x00\x00\x01\x00\x60\x4d\x54\x72\x6b\x00\x00\x00\x31\x00\xff\x03\x17\x50\x6c\x61\x79\x75\x4d\x49\x44\x49\x20\x43\x6f\x6e\x73\x75\x6d\x65\x72\x20\x54\x65\x73\x74\x00\xff\x51\x03\x07\xa1\x20\x00\xc0\x00\x00\x90\x3c\x64\x60\x80\x3c\x40\x00\xff\x2f\x00' > "$MID"

fail=0
total=0

run_case() {   # id name pattern cmd...
    local id="$1" name="$2" want="$3"; shift 3
    total=$((total+1))
    local out
    out=$("$@" 2>&1); rc=$?
    printf -- '--- [%s] %s\n$ %s\n%s\nexit=%s\n' "$id" "$name" "$*" "$out" "$rc"
    if echo "$out" | grep -qE "$want"; then
        echo "[PASS] $id $name"
    else
        echo "[FAIL] $id $name (缺少 '$want')"
        fail=$((fail+1))
    fi
}

echo "=== playumidi test_package ==="
command -v playumidi || { echo "[FAIL] playumidi not in PATH"; exit 1; }

echo "[setup] SMF 样例: $MID ($(wc -c < "$MID" 2>/dev/null || echo 0) bytes)"
if [ "$(wc -c < "$MID" 2>/dev/null || echo 0)" != "71" ]; then
    echo "[FAIL] SMF 样例生成失败（长度应为 71 字节）"
    fail=$((fail+1)); total=$((total+1))
fi

# TP1: 可执行文件可运行 + usage 输出
run_case TP1 "usage (-h)" 'usage: playumidi' playumidi -h

# TP2: 默认无 /dev/umidi* 设备时的行为（OHOS 平台事实：无 FreeBSD uMIDI 设备节点）
run_case TP2 "no umidi device (OHOS)" "Can't Open RawMidi Device" playumidi "$MID"

# TP3: 端到端 SMF 解析 + 事件播放（-0 指定 /dev/null 作为 RAW-MIDI 输出设备）
#      覆盖 OHOS 适配点：设备发现（opendir("/dev") + strlen(d_name)）与事件解析
run_case TP3 "SMF parse + play (-0 null)" '\[Title     \]: PlayuMIDI Consumer Test' \
    playumidi -0 null "$MID"

echo "=== test_package summary: $((total-fail))/$total passed ==="
[ "$fail" -eq 0 ] || exit 1
echo "✅ playumidi test_package PASSED"
