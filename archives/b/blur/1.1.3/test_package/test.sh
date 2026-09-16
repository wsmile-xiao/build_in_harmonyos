#!/usr/bin/env bash
# test_package/test.sh — blur_image 端到端冒烟（鸿蒙侧补全测试，R34/R51）
# 流程：真实 PNG 输入 → EGL pbuffer 离屏高斯模糊 → 断言输出为合法 PNG 且尺寸不变
# 覆盖两组尺寸：32x32（小图）+ 256x256（大图回归——pbuffer 必须按图像尺寸创建，
# 否则 >pbuffer 的回读越界为未定义行为，W4 审计 P1 修复的回归锚点）
# 运行环境 conanrun：PATH 含 blur/1.1.3 的 bin/，LD_LIBRARY_PATH 含 gdk-pixbuf 链
# fixture 以 base64 文本随仓（test_in*.png.b64）：GitCode PR diff 端点不携带
# 二进制补丁数据，CI checkout-pr 的 git apply 对二进制文件必失败（PR #9334 实测）
set -euo pipefail

BLUR="${1:-blur_image}"
DIR="$(cd "$(dirname "$0")" && pwd)"
OUT="${TMPDIR:-$HOME/tmp}/blur_test_out.png"   # /tmp 只读（E002），用 $TMPDIR（兜底 $HOME/tmp）
mkdir -p "$(dirname "$OUT")" 2>/dev/null || true
rm -f "$OUT"

# fixture 解码：.b64 文本 → PNG（落到 $OUT 同目录，源目录只读不应写入）
decode_fixture() {
    local B64="$1" PNG
    PNG="$(dirname "$OUT")/$(basename "${B64%.b64}")"
    base64 -d "$DIR/$B64" > "$PNG"
    echo "$PNG"
}
IN_SMALL="$(decode_fixture test_in.png.b64)"
IN_BIG="$(decode_fixture test_in_big.png.b64)"

# 单图断言套件：$1=fixture $2=期望宽 $3=期望高
run_case() {
    local IN="$1" WANT_W="$2" WANT_H="$3"

    # 断言 a：入口 fixture 合法（PNG 魔数）
    if ! head -c 8 "$IN" | od -An -tx1 | grep -q "89 50 4e 47"; then
        echo "FAIL: $IN is not a valid PNG"; return 1
    fi
    echo "PASS: input fixture $(basename "$IN") is a PNG"

    # 断言 b：端到端渲染退出码 0（EGL 上下文 + GLES3 shader 编译 + UBO 渲染 + 回读 + gdk-pixbuf 编码）
    # musl getopt 无 GNU 参数重排：选项必须置于位置参数之前
    "$BLUR" -o "$OUT" -r 11 -p 2 "$IN"
    echo "PASS: blur_image rendered exit=0"

    # 断言 c：输出存在且为合法 PNG
    [ -s "$OUT" ] || { echo "FAIL: output not created/empty"; return 1; }
    if ! head -c 8 "$OUT" | od -An -tx1 | grep -q "89 50 4e 47"; then
        echo "FAIL: output is not a PNG"; return 1
    fi
    echo "PASS: output is a valid PNG ($(wc -c < "$OUT") bytes)"

    # 断言 d：输出尺寸不变（IHDR 第 16-23 字节大端宽高）
    # toybox sh 不支持 $(( $(cmd) * n )) 嵌套命令替换，用 set -- 展开位置参数
    set -- $(od -An -tu1 -j16 -N8 "$OUT")
    local w=$(( ($1 << 24) | ($2 << 16) | ($3 << 8) | $4 ))
    local h=$(( ($5 << 24) | ($6 << 16) | ($7 << 8) | $8 ))
    [ "$w" -eq "$WANT_W" ] && [ "$h" -eq "$WANT_H" ] || {
        echo "FAIL: output dims ${w}x${h}, want ${WANT_W}x${WANT_H}"; return 1; }
    echo "PASS: output dims ${WANT_W}x${WANT_H} preserved"

    # 断言 e：模糊确实生效——输出与输入字节内容不同
    if cmp -s "$IN" "$OUT"; then
        echo "FAIL: output identical to input (blur did nothing?)"; return 1
    fi
    echo "PASS: output differs from input (blur applied)"
}

echo "== case 1: small image 32x32 =="
run_case "$IN_SMALL" 32 32

echo "== case 2: large image 256x256 (pbuffer-size regression, W4 P1) =="
run_case "$IN_BIG" 256 256

echo "ALL 10 ASSERTIONS PASSED (2 cases x 5 assertions)"
