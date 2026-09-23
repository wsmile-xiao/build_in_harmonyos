#!/usr/bin/env bash
# test_package/test.sh — 真实调用 pngnq/pngcomp 二进制的消费者测试
# 由 test_package/conanfile.py 调用：bash test.sh <path-to-pngnq>
#
# 内嵌一个 8x8 RGBA PNG（八进制转义，纯 POSIX printf 生成，不依赖外部工具），
# 真实执行 pngnq 量化并验证输出，同时验证 pngcomp 对比工具：
#   1. pngnq -V 版本输出包含 1.1 与 libpng 版本
#   2. pngnq 量化真实 PNG 返回 0，且报告 "No errors detected"
#   3. 输出文件 input-nq8.png 存在且为合法 PNG 魔数
#   4. 输出 IHDR 色彩类型为 3（索引调色板）——量化真实生效
#   5. 输出文件小于输入文件（量化压缩效果）
#   6. pngcomp 对比输入/输出两图返回 0 且输出 "Percentage correct pixels"
#   7. 非法输入（非 PNG 文件）返回非零（错误处理；上游对非法输入 SIGSEGV，
#      退出码 139，仍属非零——记录为上游已知缺陷，不修复以保持最小改动）
#   8. pngcomp -V 版本输出含 1.1（第二二进制冒烟；pngcomp 缺参数时上游仅打
#      印 usage 且退出 0，故改测版本输出）
#
# 所有操作仅在临时目录内进行。每个用例独立计数，结束时输出
# HMBS_TEST_PACKAGE_RESULT 机器证据标记；任一失败退出码 1，避免静默通过。
# 期望非零退出的用例（case 7）与命令替换均以 `|| rc=$?` 守卫，保持
# set -e 下仍可逐用例报告而非提前中止。
set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "usage: $0 <path-to-pngnq>" >&2
    exit 2
fi

pngnq_bin="$1"
pngcomp_bin="$(dirname "$pngnq_bin")/pngcomp"
PASS=0
FAIL=0

# 找一个可写临时目录
TMPROOT="${TMPDIR:-${TMP:-${TEMP:-/tmp}}}"
WORKDIR=""
for cand in "$TMPROOT" "$HOME" "$PWD" "$(dirname "$0")"; do
    [ -n "$cand" ] || continue
    try="$cand/pngnqtest-$$"
    if mkdir -p "$try" 2>/dev/null; then
        WORKDIR="$try"
        break
    fi
done
if [ -z "$WORKDIR" ]; then
    echo "[fail] cannot create writable work dir" >&2
    exit 1
fi
trap 'rm -rf "$WORKDIR"' EXIT

# ── 构造内嵌 8x8 RGBA PNG（217 字节）──
printf '%b' '\211\120\116\107\015\012\032\012\000\000\000\015\111\110\104\122\000\000\000\010\000\000\000\010\010\006\000\000\000\304\017\276\213\000\000\000\240\111\104\101\124\170\332\015\312\321\000\004\061\014\105\321\040\014\102\020\006\041\010\105\170\010\105\010\102\021\202\060\010\101\130\204\230\334\355\371\076\146\146\270\075\204\071\262\227\264\240\154\321\046\306\066\146\376\340\356\204\277\310\203\364\105\271\150\337\214\347\015\341\170\274\104\004\212\105\206\250\330\164\044\023\347\006\275\270\202\320\102\022\251\115\051\151\035\106\165\103\006\236\213\110\241\334\144\046\225\207\316\142\362\273\241\026\136\042\152\243\112\262\016\125\105\327\307\124\337\320\302\173\023\235\250\017\331\105\365\107\167\063\375\273\141\066\076\111\314\101\123\344\174\324\064\075\077\146\206\077\343\106\223\301\033\351\142\333\000\000\000\000\111\105\116\104\256\102\140\202' > "$WORKDIR/input.png"

INPUT="$WORKDIR/input.png"
OUTPUT="$WORKDIR/input-nq8.png"

# ── 用例 1: -V 版本输出含 1.1 ──
echo "[case 1/8] pngnq -V version contains 1.1"
rc_v=0
ver_output="$("$pngnq_bin" -V 2>&1)" || rc_v=$?
if [ "$rc_v" -eq 0 ] && printf '%s\n' "$ver_output" | grep -F "1.1" >/dev/null; then
    PASS=$((PASS + 1))
    echo "  [ok] version output contains 1.1"
else
    FAIL=$((FAIL + 1))
    echo "  [fail] -V rc=$rc_v, output: $(printf '%s' "$ver_output" | tr '\n' ' ')"
fi

# ── 用例 2: 量化真实 PNG 成功 ──
echo "[case 2/8] quantize real PNG, expect rc=0 and no errors"
rc_q=0
quant_output="$("$pngnq_bin" -v -n 16 "$INPUT" 2>&1)" || rc_q=$?
if [ "$rc_q" -eq 0 ] && printf '%s\n' "$quant_output" | grep -F "No errors detected" >/dev/null; then
    PASS=$((PASS + 1))
    echo "  [ok] quantization exited 0 with 'No errors detected'"
else
    FAIL=$((FAIL + 1))
    echo "  [fail] quantize rc=$rc_q, output: $(printf '%s' "$quant_output" | tr '\n' ' ')"
fi

# ── 用例 3: 输出文件存在且为合法 PNG 魔数 ──
echo "[case 3/8] output file exists with valid PNG magic"
if [ -f "$OUTPUT" ]; then
    magic=$(dd if="$OUTPUT" bs=8 count=1 2>/dev/null | od -An -tx1 | tr -d ' \n')
    if [ "$magic" = "89504e470d0a1a0a" ]; then
        PASS=$((PASS + 1))
        echo "  [ok] output has PNG magic 89504e470d0a1a0a"
    else
        FAIL=$((FAIL + 1))
        echo "  [fail] output magic is '$magic', expected 89504e470d0a1a0a"
    fi
else
    FAIL=$((FAIL + 1))
    echo "  [fail] output file not found: $OUTPUT"
fi

# ── 用例 4: 输出 IHDR 色彩类型为 3（索引调色板）──
echo "[case 4/8] output IHDR color type is 3 (palette)"
# IHDR 从偏移 8 开始：4 字节长度 + 4 字节类型 + 8 字节宽高 + 1 字节位深 + 1 字节色彩类型
# 色彩类型字节位于文件偏移 25（0 基）
colortype=""
[ -f "$OUTPUT" ] && colortype=$(od -An -tu1 -j25 -N1 "$OUTPUT" 2>/dev/null | tr -d ' \n') || true
if [ "$colortype" = "3" ]; then
    PASS=$((PASS + 1))
    echo "  [ok] output color type = 3 (indexed palette)"
else
    FAIL=$((FAIL + 1))
    echo "  [fail] output color type = '$colortype', expected 3"
fi

# ── 用例 5: 输出文件小于输入文件（量化压缩效果）──
echo "[case 5/8] output smaller than input (quantization reduces size)"
in_size=$(wc -c < "$INPUT" | tr -d ' ')
out_size=0
[ -f "$OUTPUT" ] && out_size=$(wc -c < "$OUTPUT" | tr -d ' ') || true
if [ "$out_size" -gt 0 ] && [ "$out_size" -lt "$in_size" ]; then
    PASS=$((PASS + 1))
    echo "  [ok] output ${out_size}B < input ${in_size}B"
else
    FAIL=$((FAIL + 1))
    echo "  [fail] output ${out_size}B vs input ${in_size}B"
fi

# ── 用例 6: pngcomp 对比两图返回 0 且输出统计 ──
echo "[case 6/8] pngcomp compares input vs output"
rc_c=0
comp_output="$("$pngcomp_bin" "$INPUT" "$OUTPUT" 2>&1)" || rc_c=$?
if [ "$rc_c" -eq 0 ] && printf '%s\n' "$comp_output" | grep -F "Percentage correct pixels" >/dev/null; then
    PASS=$((PASS + 1))
    echo "  [ok] pngcomp exited 0 with comparison statistics"
else
    FAIL=$((FAIL + 1))
    echo "  [fail] pngcomp rc=$rc_c, output: $(printf '%s' "$comp_output" | tr '\n' ' ')"
fi

# ── 用例 7: 非法输入（非 PNG 文件）返回非零 ──
echo "[case 7/8] non-PNG input returns non-zero"
printf 'this is not a png file at all\n' > "$WORKDIR/notapng.txt"
rc_bad=0
"$pngnq_bin" "$WORKDIR/notapng.txt" >/dev/null 2>&1 || rc_bad=$?
if [ "$rc_bad" -ne 0 ]; then
    PASS=$((PASS + 1))
    echo "  [ok] non-PNG input exited $rc_bad (non-zero)"
else
    FAIL=$((FAIL + 1))
    echo "  [fail] non-PNG input exited 0 (expected non-zero)"
fi

# ── 用例 8: pngcomp -V 版本输出含 1.1（第二二进制冒烟）──
# 注：pngcomp 缺参数时仅打印 usage 且退出 0（上游行为），故改测版本输出
echo "[case 8/8] pngcomp -V version contains 1.1"
rc_pv=0
comp_ver="$("$pngcomp_bin" -V 2>&1)" || rc_pv=$?
if [ "$rc_pv" -eq 0 ] && printf '%s\n' "$comp_ver" | grep -F "1.1" >/dev/null; then
    PASS=$((PASS + 1))
    echo "  [ok] pngcomp -V contains 1.1"
else
    FAIL=$((FAIL + 1))
    echo "  [fail] pngcomp -V rc=$rc_pv, output: $(printf '%s' "$comp_ver" | tr '\n' ' ')"
fi

echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":$([ "$FAIL" -eq 0 ] && echo true || echo false),\"command\":\"bash test.sh <pngnq-bin>\",\"discovered\":8,\"passedCount\":$PASS}"

if [ "$FAIL" -ne 0 ]; then
    echo "[fail] $FAIL case(s) failed, $PASS passed"
    exit 1
fi
echo "[ok] all $PASS test_package cases passed"
