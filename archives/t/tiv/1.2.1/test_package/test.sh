#!/data/service/hnp/bin/bash
# test_package/test.sh — tiv 1.2.1 消费者测试
#
# 通过 conanrun 的 PATH 调用打包后的 bin/tiv（不硬编码 $package_folder，
# 否则 CI L1e 把 bin/ 移走后测试仍会通过 = 空壳测试）。
# CI worker 是原生 aarch64 OHOS 设备，二进制直接执行，不用 qemu。
set -eu

PASS=0
FAIL=0

ok() {
    PASS=$((PASS + 1))
    echo "[ok] $1"
}

bad() {
    FAIL=$((FAIL + 1))
    echo "[fail] $1"
}

assert_eq() { # $1=期望 $2=实际 $3=描述
    if [ "$1" = "$2" ]; then
        ok "$3 (= $2)"
    else
        bad "$3: 期望 '$1', 实际 '$2'"
    fi
}

assert_contains() { # $1=haystack $2=needle $3=描述
    case "$1" in
        *"$2"*) ok "$3" ;;
        *)      bad "$3: 输出里找不到 '$2'" ;;
    esac
}

assert_not_contains() { # $1=haystack $2=needle $3=描述
    case "$1" in
        *"$2"*) bad "$3: 输出里不该出现 '$2'" ;;
        *)      ok "$3" ;;
    esac
}

# assert_not_contains 在「输出为空」时会真空转绿（空串当然不含 needle）。
# 所以每份被捕获的输出都必须先过这道非空守卫，反向断言才有意义。
assert_nonempty() { # $1=haystack $2=描述
    if [ -n "$1" ]; then
        ok "$2 ($(printf '%s' "$1" | wc -c | tr -d ' ') 字节)"
    else
        bad "$2: 捕获到的输出是空的"
    fi
}

# 工作目录：优先 $TMPDIR（R10：OHOS 上 /tmp 只读），否则退回当前目录下的
# .tiv_test_tmp。退出时清理，避免把测试产物留在配方目录里（JC1 垃圾检查）。
WORK="${TMPDIR:-}/.tiv_test_tmp"
[ -d "${TMPDIR:-}" ] || WORK="$(pwd)/.tiv_test_tmp"
rm -rf "$WORK"
mkdir -p "$WORK"
trap 'rm -rf "$WORK"' EXIT
cd "$WORK"

ESC="$(printf '\033')"
# Unicode 半块字符的 UTF-8 字节：U+2580 ▀ (e2 96 80)、U+2584 ▄ (e2 96 84)
BLOCK_UPPER=$'\xe2\x96\x80'
BLOCK_LOWER=$'\xe2\x96\x84'

# ── 生成测试用图片（纯 bash，不依赖 python/ImageMagick）────────────────
# 64x64 彩色 PPM（P6）：R 随 x 递增、G 随 y 递增，便于验证缩放方向
gen_rgb_ppm() { # $1=输出文件 $2=宽 $3=高
    local f="$1" w="$2" h="$3" x y
    {
        printf 'P6\n%s %s\n255\n' "$w" "$h"
        y=0
        while [ "$y" -lt "$h" ]; do
            x=0
            while [ "$x" -lt "$w" ]; do
                printf "\\x$(printf '%02x' $((x * 4 % 256)))"
                printf "\\x$(printf '%02x' $((y * 8 % 256)))"
                printf '\xc0'
                x=$((x + 1))
            done
            y=$((y + 1))
        done
    } > "$f"
}

# 8x8 灰度 PPM（P5）：CImg 读进来 spectrum()==1，tiv 需复制到 3 通道
gen_gray_ppm() {
    local f="$1" x y
    {
        printf 'P5\n8 8\n255\n'
        y=0
        while [ "$y" -lt 8 ]; do
            x=0
            while [ "$x" -lt 8 ]; do
                printf "\\x$(printf '%02x' $((32 + x * 16)))"
                x=$((x + 1))
            done
            y=$((y + 1))
        done
    } > "$f"
}

gen_rgb_ppm rgb.ppm 64 64
gen_gray_ppm gray.ppm
[ -s rgb.ppm ] || { echo "[fail] 无法生成 rgb.ppm"; exit 1; }
[ -s gray.ppm ] || { echo "[fail] 无法生成 gray.ppm"; exit 1; }

# ── 1. 二进制可从 PATH 找到（conanrun 已把 bin/ 放进 PATH）─────────────
TIV_PATH="$(command -v tiv || true)"
if [ -n "$TIV_PATH" ] && [ -x "$TIV_PATH" ]; then
    ok "tiv 在 PATH 中可执行: $TIV_PATH"
else
    bad "PATH 里找不到可执行的 tiv"
    echo "--- 结果: $PASS passed, $FAIL failed"
    exit 1
fi

# 1b. 光「PATH 里有」不够：宿主上恰好装了同名 tiv 时，空壳测试照样全绿。
#     要求 PATH 上的 tiv 落在依赖包自己的 bin/ 里（TIV_PKG_DIR 由
#     test_package/conanfile.py 从 dependencies[tested_reference_str]
#     .package_folder 传入）。
TIV_REAL_DIR="$(cd "$(dirname "$TIV_PATH")" && pwd)"
if [ -n "${TIV_PKG_DIR:-}" ] && [ "$TIV_REAL_DIR" = "$TIV_PKG_DIR/bin" ]; then
    ok "PATH 上的 tiv 就是依赖包 bin/ 里的文件 ($TIV_REAL_DIR)"
else
    bad "PATH 上的 tiv 不在依赖包 bin/ 下: '$TIV_REAL_DIR' != '${TIV_PKG_DIR:-<未传入>}/bin'"
fi

# ── 2. 版本横幅 ───────────────────────────────────────────────────────
HELP_OUT="$(tiv --help 2>&1 || true)"
assert_nonempty "$HELP_OUT" "--help 有输出"
assert_contains "$HELP_OUT" "Terminal Image Viewer v1.2.1" "--help 打印版本横幅 v1.2.1"
assert_contains "$HELP_OUT" "usage: tiv [options] <image>" "--help 打印 usage 行"

set +e
tiv --help >/dev/null 2>&1
assert_eq 0 "$?" "--help 退出码 0"

# 无参数也应打印 usage 并退出 0（上游行为）
NOARG_OUT="$(tiv 2>&1 || true)"
assert_contains "$NOARG_OUT" "usage: tiv [options] <image>" "无参数时打印 usage"

# ── 3. 参数错误路径（sysexits.h 约定的退出码）──────────────────────────
tiv --bogus-option >/dev/null 2>&1
assert_eq 64 "$?" "未知选项退出码 64 (EX_USAGE)"

tiv /nonexistent/nope.ppm >/dev/null 2>&1
assert_eq 66 "$?" "文件不存在退出码 66 (EX_NOINPUT)"

# ── 4. 基本渲染：24-bit RGB 转义序列 + Unicode 半块字符 ────────────────
tiv -w 40 -h 8 rgb.ppm >render.txt 2>/dev/null
RENDER="$(cat render.txt)"
assert_nonempty "$RENDER" "24-bit 渲染有输出"
assert_contains "$RENDER" "${ESC}[48;2;" "输出含 24-bit 背景色转义序列 (ESC[48;2;r;g;b)"
assert_contains "$RENDER" "${ESC}[38;2;" "输出含 24-bit 前景色转义序列 (ESC[38;2;r;g;b)"
assert_contains "$RENDER" "${ESC}[0m" "输出以 ESC[0m 复位颜色"
assert_contains "$RENDER" "$BLOCK_LOWER" "输出含 Unicode 下半块字符 U+2584 (e2 96 84)"

# ── 5. -h 决定输出行数（-h N → N 行，maxHeight = 8*N 像素）──────────────
tiv -w 40 -h 4 rgb.ppm 2>/dev/null | wc -l | tr -d ' ' > lines4.txt
tiv -w 40 -h 8 rgb.ppm 2>/dev/null | wc -l | tr -d ' ' > lines8.txt
assert_eq 4 "$(cat lines4.txt)" "-h 4 输出 4 行"
assert_eq 8 "$(cat lines8.txt)" "-h 8 输出 8 行"

# ── 6. -w 改变缩放后的输出规模 ─────────────────────────────────────────
tiv -w 10 -h 8 rgb.ppm 2>/dev/null | wc -c | tr -d ' ' > bytes_w10.txt
tiv -w 20 -h 8 rgb.ppm 2>/dev/null | wc -c | tr -d ' ' > bytes_w20.txt
if [ "$(cat bytes_w10.txt)" != "$(cat bytes_w20.txt)" ]; then
    ok "-w 10 与 -w 20 输出字节数不同（缩放生效: $(cat bytes_w10.txt) vs $(cat bytes_w20.txt)）"
else
    bad "-w 10 与 -w 20 输出字节数相同，-w 似乎未生效"
fi

# ── 7. --256 走 256 色索引模式（ESC[48;5;N / ESC[38;5;N）──────────────
tiv --256 -w 40 -h 8 rgb.ppm >c256.txt 2>/dev/null
C256="$(cat c256.txt)"
assert_nonempty "$C256" "--256 渲染有输出"
assert_contains "$C256" "${ESC}[48;5;" "--256 输出含 256 色背景序列 (ESC[48;5;N)"
assert_contains "$C256" "${ESC}[38;5;" "--256 输出含 256 色前景序列 (ESC[38;5;N)"
assert_not_contains "$C256" "${ESC}[48;2;" "--256 模式不再使用 24-bit 序列"

# ── 8. -0 关闭块字符优化：固定用 ▄（U+2584），不挑最佳块字符 ──────────
# 条纹图：每 8 行中第 0-5 行亮（224,224,224）、第 6-7 行暗（16,16,16），
# 对应位图 0x000000ff。默认模式在 BITMAPS 表里匹配到「下 1/4 块」U+2582，
# -0 则固定输出「下半块」U+2584 —— 两者可区分。
gen_stripe_ppm() {
    local f="$1" x y
    {
        printf 'P6\n32 8\n255\n'
        y=0
        while [ "$y" -lt 8 ]; do
            x=0
            while [ "$x" -lt 32 ]; do
                if [ "$y" -lt 6 ]; then
                    printf '\xe0\xe0\xe0'
                else
                    printf '\x10\x10\x10'
                fi
                x=$((x + 1))
            done
            y=$((y + 1))
        done
    } > "$f"
}
gen_stripe_ppm stripe.ppm
tiv -w 40 -h 8 stripe.ppm >stripe_def.txt 2>/dev/null
tiv -0 -w 40 -h 8 stripe.ppm >stripe_noopt.txt 2>/dev/null
STRIPE_DEF="$(cat stripe_def.txt)"
STRIPE_NOOPT="$(cat stripe_noopt.txt)"
BLOCK_LOWER_QUARTER=$'\xe2\x96\x82'   # ▂ U+2582 下 1/4 块
assert_nonempty "$STRIPE_DEF" "条纹图默认模式渲染有输出"
assert_nonempty "$STRIPE_NOOPT" "-0 模式渲染有输出"
assert_contains "$STRIPE_DEF" "$BLOCK_LOWER_QUARTER" "条纹图默认模式选中最佳块字符 U+2582"
assert_not_contains "$STRIPE_NOOPT" "$BLOCK_LOWER_QUARTER" "-0 模式不选最佳块字符"
assert_contains "$STRIPE_NOOPT" "$BLOCK_LOWER" "-0 模式固定用 U+2584 (e2 96 84)"
assert_contains "$STRIPE_NOOPT" "${ESC}[48;2;" "-0 模式仍输出 24-bit 序列"
assert_not_contains "$STRIPE_DEF" "$BLOCK_LOWER" "条纹图默认模式未退化成固定 U+2584"

# ── 9. 灰度图（P5）被复制到 3 通道：前景色 R=G=B ───────────────────────
# 上游 load_rgb_CImg()：spectrum()==1 时把灰度值复制到 3 个通道。
tiv -w 8 -h 4 gray.ppm >gray.txt 2>/dev/null
GRAY="$(cat gray.txt)"
assert_nonempty "$GRAY" "灰度图渲染有输出"
FG="$(printf '%s' "$GRAY" | grep -oE '38;2;[0-9]+;[0-9]+;[0-9]+' | head -1 | cut -d';' -f3,4,5)"
if [ -n "$FG" ]; then
    R="$(printf '%s' "$FG" | cut -d';' -f1)"
    G="$(printf '%s' "$FG" | cut -d';' -f2)"
    B="$(printf '%s' "$FG" | cut -d';' -f3)"
    if [ "$R" = "$G" ] && [ "$G" = "$B" ]; then
        ok "灰度图前景色三通道相等 (R=$R G=$G B=$B)，spectrum==1 → 3 通道复制生效"
    else
        bad "灰度图前景色三通道不相等 (R=$R G=$G B=$B)"
    fi
    # 背景色同样应为灰度
    BG="$(printf '%s' "$GRAY" | grep -oE '48;2;[0-9]+;[0-9]+;[0-9]+' | head -1 | cut -d';' -f3,4,5)"
    BR="$(printf '%s' "$BG" | cut -d';' -f1)"
    BG2="$(printf '%s' "$BG" | cut -d';' -f2)"
    BB="$(printf '%s' "$BG" | cut -d';' -f3)"
    if [ "$BR" = "$BG2" ] && [ "$BG2" = "$BB" ]; then
        ok "灰度图背景色三通道相等 (R=$BR G=$BG2 B=$BB)"
    else
        bad "灰度图背景色三通道不相等 (R=$BR G=$BG2 B=$BB)"
    fi
else
    bad "灰度图渲染输出里找不到 24-bit 前景色序列"
fi

# ── 10. dir 模式：多文件缩略图 ─────────────────────────────────────────
mkdir -p gallery
cp rgb.ppm gallery/one.ppm
cp gray.ppm gallery/two.ppm
set +e
tiv -d -w 40 gallery >dir.txt 2>/dev/null
DIR_RC=$?
set -e
assert_eq 0 "$DIR_RC" "dir 模式渲染 gallery 退出码 0"
DIR_OUT="$(cat dir.txt)"
assert_nonempty "$DIR_OUT" "dir 模式渲染有输出"
assert_contains "$DIR_OUT" "${ESC}[48;2;" "dir 模式输出含 24-bit 序列"

# ── 结果 ───────────────────────────────────────────────────────────────
echo "--- 结果: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] || exit 1
exit 0