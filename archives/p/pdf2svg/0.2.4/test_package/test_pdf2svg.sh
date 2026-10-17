#!/bin/sh
# test_pdf2svg.sh — 真实执行**已安装的** bin/pdf2svg（R34：二进制即被测 API）
#
# 由 test_package/conanfile.py test() 调用：
#   $1 = 已安装的 bin/pdf2svg 绝对路径
#   $2 = 冒号分隔的 LD_PRELOAD 列表（从被测二进制的 DT_NEEDED 出发 BFS 得到的
#        依赖包 .so 绝对路径；HMBS [stale_runtime_library]：OHOS loader 可能
#        忽略 LD_LIBRARY_PATH）
#   $3 = 可写 scratch 目录，其中已由 conanfile 写好 fixture.pdf
#        （OHOS 的 /tmp 是 erofs 只读，E002）
#
# 仅用 POSIX sh（HMBS [shell_getcwd]：用注入的 SHELL 执行，不硬编码
# /data/service/hnp/bin/bash）。不用 set -e/-u/pipefail（toybox ash 拒绝），
# 每条断言自己收 rc 并始终打印输出，让加载器错误能进日志。
#
# 覆盖范围（6 项可观测行为）：用法输出 → 单页转换（默认第 1 页）→ `all`
# 多页转换 → 输入文件打不开 → 页标签不存在 → 两页渲染结果不同。
# pdf2svg.c 的退出码是负值取低 8 位：-2→254(用法) -3→253(打不开)
# -4→252(转换失败) -5→251(页数超限)。
#
# 夹具是 2 页纯矢量（无字体）PDF：渲染路径不经过 fontconfig/freetype 的字体
# 匹配，CI worker 上没有字体也不影响断言。

PDF2SVG="$1"
LD_PRELOAD_EXTRA="${2:-}"
WORK="${3:-}"

if [ -z "$PDF2SVG" ]; then
    echo "FAIL: pdf2svg binary path not provided"
    exit 1
fi

if [ ! -x "$PDF2SVG" ]; then
    echo "FAIL: $PDF2SVG not found or not executable"
    exit 1
fi

if [ -z "$WORK" ] || [ ! -d "$WORK" ]; then
    echo "FAIL: writable scratch dir not provided (arg 3)"
    exit 1
fi

if [ ! -s "$WORK/fixture.pdf" ]; then
    echo "FAIL: fixture.pdf missing in $WORK"
    exit 1
fi

BIN_DIR=$(dirname "$PDF2SVG")
export LD_LIBRARY_PATH="${BIN_DIR}:${LD_LIBRARY_PATH:-}"
if [ -n "$LD_PRELOAD_EXTRA" ]; then
    export LD_PRELOAD="$LD_PRELOAD_EXTRA"
fi
# 少数依赖（fontconfig 的 cache 等）会写临时目录；/tmp 只读，指到 scratch。
export TMPDIR="$WORK"
export TMP="$WORK"
export TEMP="$WORK"

echo "[shell] $0"
echo "[env] LD_LIBRARY_PATH=$LD_LIBRARY_PATH"
echo "[env] LD_PRELOAD entries=$(printf '%s' "${LD_PRELOAD:-}" | tr ':' '\n' | grep -c . )"
echo "[env] WORK=$WORK"
echo "[fixture] $(wc -c < "$WORK/fixture.pdf") bytes"

discovered=6
passed=0

# ── 1. 无参数 → 用法输出到 stdout，退出码 254（main() return -2） ──────
echo "[test 1/$discovered] pdf2svg (no args)"
usage_output=$("$PDF2SVG" 2>&1)
rc=$?
echo "$usage_output"
if [ $rc -eq 254 ] && echo "$usage_output" | grep -q "Usage: pdf2svg"; then
    echo "PASS: no-args prints usage and exits 254"
    passed=$((passed + 1))
else
    echo "FAIL: no-args exit=$rc output=[$usage_output]"
fi

# ── 2. 单页转换（不给页号 → 默认第 1 页）→ exit 0 且产物是 SVG ─────────
echo "[test 2/$discovered] pdf2svg fixture.pdf out1.svg"
"$PDF2SVG" "$WORK/fixture.pdf" "$WORK/out1.svg" > "$WORK/convert1.out" 2>&1
rc=$?
cat "$WORK/convert1.out"
if [ $rc -eq 0 ] && [ -s "$WORK/out1.svg" ] && grep -q "<svg" "$WORK/out1.svg"; then
    echo "PASS: single page converted, out1.svg is a non-empty SVG ($(wc -c < "$WORK/out1.svg") bytes)"
    passed=$((passed + 1))
else
    echo "FAIL: convert exit=$rc, out1.svg missing/empty/not SVG"
fi

# ── 3. `all` 模式：输出参数是 printf 格式串，2 页 → all-1.svg + all-2.svg ──
echo "[test 3/$discovered] pdf2svg fixture.pdf all-%d.svg all"
"$PDF2SVG" "$WORK/fixture.pdf" "$WORK/all-%d.svg" all > "$WORK/convert_all.out" 2>&1
rc=$?
cat "$WORK/convert_all.out"
if [ $rc -eq 0 ] && [ -s "$WORK/all-1.svg" ] && [ -s "$WORK/all-2.svg" ]; then
    echo "PASS: all-pages mode produced all-1.svg and all-2.svg"
    passed=$((passed + 1))
else
    echo "FAIL: all-mode exit=$rc, per-page files missing or empty"
fi

# ── 4. 输入文件不存在 → "Unable to open file" 到 stderr，退出码 253（-3） ──
echo "[test 4/$discovered] pdf2svg no-such-file.pdf out4.svg"
"$PDF2SVG" "$WORK/no-such-file.pdf" "$WORK/out4.svg" > "$WORK/convert4.out" 2>&1
rc=$?
cat "$WORK/convert4.out"
if [ $rc -eq 253 ] && grep -q "Unable to open file" "$WORK/convert4.out"; then
    echo "PASS: missing input reports 'Unable to open file' and exits 253"
    passed=$((passed + 1))
else
    echo "FAIL: missing-input exit=$rc (expected 253)"
fi

# ── 5. 页标签不存在 → "Page does not exist"，退出码 252（-4） ──────────
echo "[test 5/$discovered] pdf2svg fixture.pdf out5.svg 99"
"$PDF2SVG" "$WORK/fixture.pdf" "$WORK/out5.svg" 99 > "$WORK/convert5.out" 2>&1
rc=$?
cat "$WORK/convert5.out"
if [ $rc -eq 252 ] && grep -q "Page does not exist" "$WORK/convert5.out"; then
    echo "PASS: unknown page label reports 'Page does not exist' and exits 252"
    passed=$((passed + 1))
else
    echo "FAIL: unknown-page exit=$rc (expected 252)"
fi

# ── 6. 两页内容不同 → 渲染产物必须不同（证明按页取页而不是重复第 1 页） ──
echo "[test 6/$discovered] all-1.svg vs all-2.svg"
if [ -s "$WORK/all-1.svg" ] && [ -s "$WORK/all-2.svg" ] \
        && [ "$(cat "$WORK/all-1.svg")" != "$(cat "$WORK/all-2.svg")" ]; then
    echo "PASS: page 1 and page 2 render to different SVGs"
    passed=$((passed + 1))
else
    echo "FAIL: per-page SVG output identical or missing"
fi

if [ "$passed" -ne "$discovered" ]; then
    echo "FAIL: $((discovered - passed))/$discovered checks failed"
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"test_pdf2svg.sh","discovered":%d,"passedCount":%d}\n' \
        "$discovered" "$passed"
    exit 1
fi

echo "OK: all $discovered checks passed"
printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"test_pdf2svg.sh","discovered":%d,"passedCount":%d}\n' \
    "$discovered" "$passed"
exit 0
