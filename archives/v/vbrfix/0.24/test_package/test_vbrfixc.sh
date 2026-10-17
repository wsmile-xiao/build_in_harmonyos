#!/data/service/hnp/bin/bash
# test_vbrfixc.sh — vbrfixc 消费者功能测试（conan test_package 入口）
#
# 用法:   bash test_vbrfixc.sh <bin_dir>
# 退出码: 0 = 全部用例通过；1 = 存在失败用例；2 = 参数错误
#
# 本脚本实质调用被测包（R34）：对合成 MP3 样本实际运行 <bin_dir>/vbrfixc，
# 并校验输出产物的结构（Xing 头、ID3 标签保留、CBR 拒写等）。
#
# 用例清单（9 项，其中 1 项为鸿蒙平台专有）：
#   TC-01-usage          无参数用法输出
#   TC-02-vbr-no-xing    VBR 且无 Xing 头 → 重建 VBR 头
#   TC-03-vbr-with-xing  VBR 且已有 Xing 头 → 识别并重建
#   TC-04-cbr-refused    CBR 且无 -allways → 拒写（错误路径）
#   TC-05-cbr-allways    CBR + -allways → 强制写出
#   TC-06-id3v1-kept     ID3v1 标签保留
#   TC-07-id3v2-kept     ID3v2 标签保留
#   TC-08-cbr-makevbr    CBR + -allways -makevbr → 生成 VBR 头
#   TC-09-ohos-abi       【鸿蒙特有】产物为 OHOS 目标 AArch64 ELF 且可在本机执行

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ $# -lt 1 ]; then
    echo "usage: $0 <bin_dir>" >&2
    exit 2
fi
BIN_DIR="$1"
VBRFIXC="$BIN_DIR/vbrfixc"

if [ ! -x "$VBRFIXC" ]; then
    echo "FAIL: $VBRFIXC 不存在或不可执行" >&2
    exit 1
fi

WORK="$(mktemp -d)"
LOGS="$WORK/logs"
mkdir -p "$LOGS" "$WORK/run"

TOTAL=0
PASS=0
FAIL=0
SKIP=0
CUR=""
RESULTS=()

case_begin() {
    CUR="$1"
    TOTAL=$((TOTAL + 1))
    mkdir -p "$WORK/run/$CUR"
    rm -f "$WORK/run/$CUR/out.mp3"
    echo "── [$CUR] $2"
}
case_pass() {
    PASS=$((PASS + 1))
    RESULTS+=("PASS  $CUR")
    echo "   → PASS${1:+ ($1)}"
}
case_fail() {
    FAIL=$((FAIL + 1))
    RESULTS+=("FAIL  $CUR — $1")
    echo "   → FAIL: $1"
}
case_skip() {
    SKIP=$((SKIP + 1))
    RESULTS+=("SKIP  $CUR — $1")
    echo "   → SKIP: $1"
}

# 在独立目录中运行被测二进制；输出捕获到日志
run_tool() {
    local tag="$1"; shift
    (
        cd "$WORK/run/$CUR" || exit 9
        "$VBRFIXC" "$@"
    ) >"$LOGS/$tag.stdout" 2>"$LOGS/$tag.stderr"
    return $?
}

# python 断言助手
vfy() {
    python3 "$SCRIPT_DIR/verify.py" "$@"
}

gen_fixture() {
    python3 "$SCRIPT_DIR/gen_mp3.py" "$1" "$WORK/run/$CUR/$1.mp3" >/dev/null
}

echo "=============================================================="
echo " vbrfixc test_package — bin_dir=$BIN_DIR"
echo " work=$WORK"
echo "=============================================================="

# ── TC-01 无参数用法 ───────────────────────────────────────────
case_begin TC-01-usage "无参数调用 → 打印用法并退出 0"
run_tool TC-01-usage
rc=$?
if [ $rc -ne 0 ]; then
    case_fail "退出码 $rc != 0"
elif ! grep -q "VbrFix Command Line Version" "$LOGS/TC-01-usage.stdout"; then
    case_fail "stdout 缺少版本标识"
elif ! grep -q -- "-makevbr" "$LOGS/TC-01-usage.stdout"; then
    case_fail "stdout 缺少用法列表"
else
    case_pass "exit=0, 用法已打印"
fi

# ── TC-02 VBR 无 Xing → 重建 ───────────────────────────────────
case_begin TC-02-vbr-no-xing "VBR(128/160k 交替, 24 帧) 无 Xing → 重建 VBR 头"
gen_fixture vbr_noxing
run_tool TC-02-vbr-no-xing vbr_noxing.mp3 out.mp3
rc=$?
if [ $rc -ne 0 ]; then
    case_fail "退出码 $rc != 0"
elif ! grep -q "DONE, ABR=144,Frames=24" "$LOGS/TC-02-vbr-no-xing.stdout"; then
    case_fail "未正确统计 24 帧/ABR=144"
elif ! grep -q "Written new vbr tag" "$LOGS/TC-02-vbr-no-xing.stdout"; then
    case_fail "未写出 VBR 头"
elif ! vfy contains "$WORK/run/TC-02-vbr-no-xing/out.mp3" Xing 1; then
    case_fail "输出缺少 Xing 头"
elif ! vfy size-delta "$WORK/run/TC-02-vbr-no-xing/out.mp3" \
        "$WORK/run/TC-02-vbr-no-xing/vbr_noxing.mp3" 417; then
    case_fail "输出大小不等于 输入+417"
else
    case_pass "24 帧识别, Xing 头重建, 输出=输入+417B"
fi

# ── TC-03 VBR 已有 Xing → 识别并重建 ──────────────────────────
case_begin TC-03-vbr-with-xing "VBR 且已有 Xing 头 → 识别旧头并重建"
gen_fixture vbr_xing
run_tool TC-03-vbr-with-xing vbr_xing.mp3 out.mp3
rc=$?
if [ $rc -ne 0 ]; then
    case_fail "退出码 $rc != 0"
elif ! grep -q "Found Xing tag at 1 with size 417" "$LOGS/TC-03-vbr-with-xing.stdout"; then
    case_fail "未识别既有 Xing 头"
elif ! vfy contains "$WORK/run/TC-03-vbr-with-xing/out.mp3" Xing 1; then
    case_fail "输出 Xing 头数量不为 1"
elif ! vfy size "$WORK/run/TC-03-vbr-with-xing/out.mp3" 11685; then
    case_fail "输出大小不为 11685"
else
    case_pass "既有 Xing 已识别, 输出仅含 1 个 Xing 头"
fi

# ── TC-04 CBR 无 -allways → 拒写 ───────────────────────────────
case_begin TC-04-cbr-refused "CBR 无 -allways → 报错且不产出文件"
gen_fixture cbr_noxing
run_tool TC-04-cbr-refused cbr_noxing.mp3 out.mp3
rc=$?
if [ $rc -ne 0 ]; then
    case_fail "退出码 $rc != 0"
elif ! grep -q "File Is Not VBR" "$LOGS/TC-04-cbr-refused.stderr"; then
    case_fail "stderr 缺少 \"File Is Not VBR\""
elif ! vfy not-exists "$WORK/run/TC-04-cbr-refused/out.mp3"; then
    case_fail "CBR 未被拒绝，仍生成了输出"
else
    case_pass "正确拒绝非 VBR 文件"
fi

# ── TC-05 CBR + -allways → 强制写出 ───────────────────────────
case_begin TC-05-cbr-allways "CBR + -allways → 强制写出（字节数不变）"
gen_fixture cbr_noxing
run_tool TC-05-cbr-allways -allways cbr_noxing.mp3 out.mp3
rc=$?
if [ $rc -ne 0 ]; then
    case_fail "退出码 $rc != 0"
elif ! grep -q "FLAGS = 32" "$LOGS/TC-05-cbr-allways.stdout"; then
    case_fail "标志位解析错误（应为 32）"
elif ! vfy size "$WORK/run/TC-05-cbr-allways/out.mp3" 10008; then
    case_fail "输出大小不为 10008"
else
    case_pass "-allways 生效, 输出=输入大小"
fi

# ── TC-06 ID3v1 保留 ──────────────────────────────────────────
case_begin TC-06-id3v1-kept "VBR + ID3v1 标签 → 标签保留到输出尾部"
gen_fixture vbr_id3v1
run_tool TC-06-id3v1-kept vbr_id3v1.mp3 out.mp3
rc=$?
if [ $rc -ne 0 ]; then
    case_fail "退出码 $rc != 0"
elif ! grep -q "Id3v1 tag found" "$LOGS/TC-06-id3v1-kept.stdout"; then
    case_fail "未识别 ID3v1 标签"
elif ! vfy id3v1-at-end "$WORK/run/TC-06-id3v1-kept/out.mp3"; then
    case_fail "输出 len-128 处缺少 ID3v1 标签"
elif ! vfy size "$WORK/run/TC-06-id3v1-kept/out.mp3" 11813; then
    case_fail "输出大小不为 11813"
else
    case_pass "ID3v1 标签在输出尾部保留"
fi

# ── TC-07 ID3v2 保留 ──────────────────────────────────────────
case_begin TC-07-id3v2-kept "VBR + ID3v2 标签 → 标签保留到输出头部"
gen_fixture vbr_id3v2
run_tool TC-07-id3v2-kept vbr_id3v2.mp3 out.mp3
rc=$?
if [ $rc -ne 0 ]; then
    case_fail "退出码 $rc != 0"
elif ! grep -q "Found Id3v2 tag with size50" "$LOGS/TC-07-id3v2-kept.stdout"; then
    case_fail "未识别 ID3v2 标签"
elif ! vfy startswith "$WORK/run/TC-07-id3v2-kept/out.mp3" ID3; then
    case_fail "输出头部缺少 ID3v2 标签"
elif ! vfy size "$WORK/run/TC-07-id3v2-kept/out.mp3" 11735; then
    case_fail "输出大小不为 11735"
else
    case_pass "ID3v2 标签在输出头部保留"
fi

# ── TC-08 CBR + -makevbr → 生成 VBR 头 ───────────────────────
case_begin TC-08-cbr-makevbr "CBR + -allways -makevbr → 强制生成 VBR 头"
gen_fixture cbr_noxing
run_tool TC-08-cbr-makevbr -allways -makevbr cbr_noxing.mp3 out.mp3
rc=$?
if [ $rc -ne 0 ]; then
    case_fail "退出码 $rc != 0"
elif ! grep -q "FLAGS = 96" "$LOGS/TC-08-cbr-makevbr.stdout"; then
    case_fail "标志位解析错误（应为 96）"
elif ! vfy contains "$WORK/run/TC-08-cbr-makevbr/out.mp3" Xing 1; then
    case_fail "输出缺少 Xing 头"
elif ! vfy size "$WORK/run/TC-08-cbr-makevbr/out.mp3" 10425; then
    case_fail "输出大小不为 10425"
else
    case_pass "-makevbr 生效, Xing 头已生成"
fi

# ── TC-09【鸿蒙特有】OHOS AArch64 产物与运行 ──────────────────
case_begin TC-09-ohos-abi "【鸿蒙特有】产物为 OHOS 目标 AArch64 ELF 且可在本机执行"
OS_NAME="$(uname -s 2>/dev/null || echo unknown)"
OS_MACH="$(uname -m 2>/dev/null || echo unknown)"
echo "   本机: $(uname -s -r -m 2>/dev/null)"
if ! vfy elf-ohos "$VBRFIXC"; then
    case_fail "产物不是 ELF64/LE/AArch64"
elif ! run_tool TC-09-ohos-abi; then
    case_fail "产物无法在本机执行"
elif [ "$OS_MACH" != "aarch64" ]; then
    case_skip "非 aarch64 运行环境（uname -m=$OS_MACH），仅校验 ELF 目标"
else
    case_pass "OS=$OS_NAME/$OS_MACH, ELF64/LE/AArch64 且执行成功"
fi

# ── 汇总 ──────────────────────────────────────────────────────
echo "=============================================================="
echo " 用例明细:"
for r in "${RESULTS[@]}"; do
    echo "   $r"
done
echo "--------------------------------------------------------------"
echo " CASE SUMMARY: total=$TOTAL passed=$PASS failed=$FAIL skipped=$SKIP"
echo " 日志目录: $LOGS"
echo "=============================================================="

if [ "$FAIL" -ne 0 ]; then
    echo "RESULT: FAIL"
    exit 1
fi
echo "RESULT: PASS"
exit 0
