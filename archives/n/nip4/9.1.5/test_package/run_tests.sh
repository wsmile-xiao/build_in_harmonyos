#!/bin/sh
# test_package/run_tests.sh — 已安装 snip 二进制的真实 CLI 冒烟断言（17 断言）
#
# 用法: sh run_tests.sh <snip_absolute_path> <work_dir>
# 退出码: 0 = 全部断言通过; 非 0 = 有断言失败
#
# 断言清单（1-9 与上游 test/test_cli.sh 的 check_output 序列逐条对应，
# 10-13 覆盖 vips 图像编码链路，14-17 为 OHOS 平台字节级检查）：
#   1.  snip -e '2 + 2'                → "4"                    (test_cli.sh: check_output)
#   2.  snip -e '"hello"'              → "hello"
#   3.  snip -e '"2" ++ "hello"'       → "2hello"
#   4.  snip -e '"hello\n"'            → "hello"
#   5.  snip -e "['a','b','c']"        → "abc"
#   6.  snip -e "[1,2,3,'a','b','c']"  → 原样回显
#   7.  snip -e "['a','b','c',1,2,3]"  → 原样回显
#   8.  snip -e "['a','b','c','d',1,2,3]" → "abcd ++ [1, 2, 3]"
#   9.  snip -e '[1..5]'               → "[1, 2, 3, 4, 5]"
#  10.  Image_file + -o → JPEG 落盘    (vips JPEG 编码链路, 真实写盘)
#  11.  JPEG 魔数 ff d8 ff             (真 JPEG 而非空壳)
#  12.  Image_file + -o → PNG 落盘     (vips PNG 编码链路)
#  13.  PNG 魔数 89 50 4e 47
#  14.  ELF magic 7f 45 4c 46          (字节级, 无需 readelf/file)
#  15.  ELFCLASS64 (byte 4 == 0x02)
#  16.  e_machine == EM_AARCH64 (0x00b7)
#  17.  share/nip4/start 可定位 (VIPSHOME 注入生效, Image_file 可解析)
#
# 不测项（环境依赖，OHOS 非交互环境不可满足，如实注释不假装绕过）：
#   - test_magick.ws: 依赖外部 ImageMagick magick CLI，OHOS 无此工具
#   - test_colour.ws: 依赖 vips gainmap/ICC 扩展字段，ohpcd vips 未编译
#   - workspace --test 全套: 由 conanfile build() 的 meson test 运行
set -u

SNIP="$1"
WORK="$2"

# 推导安装前缀并注入 VIPSHOME：已安装 snip 位于 <prefix>/bin/，
# start 数据位于 <prefix>/share/nip4/start/（Image.def 定义 Image_file）。
# Image_file 表达式依赖 $VIPSHOME 展开，缺失时断言 17 记为失败。
PREFIX=$(CDPATH= cd -- "$(dirname -- "$SNIP")/.." && pwd)
VIPSHOME_IMPORT=false
if [ -f "$PREFIX/share/nip4/start/Image.def" ]; then
    VIPSHOME="$PREFIX"
    export VIPSHOME
    VIPSHOME_IMPORT=true
fi

PASS=0
FAIL=0

note() { printf '%s\n' "$*"; }
ok()   { PASS=$((PASS + 1)); note "  PASS: $*"; }
bad()  { FAIL=$((FAIL + 1)); note "  FAIL: $*"; }

check_output() {
    # check_output <expected> <actual> <label>
    if [ "$2" = "$1" ]; then ok "$3"; else bad "$3 (expected '$1', got '$2')"; fi
}

expr_of() {
    # 表达式求值，去除可能的多余回车。stderr 不丢弃，落盘
    # $WORK/expr.stderr 供失败诊断（CI #61562 曾因 2>/dev/null
    # 掩盖 snip 启动报错，全部断言只见空输出）。
    "$SNIP" -e "$1" 2>"$WORK/expr.stderr" | tr -d '\r'
}

# expr_of 的 stderr 落盘依赖 $WORK 已存在，必须先建目录
# （此前 mkdir 在断言 10 之后，导致断言 1-9 的重定向失败、snip 未执行）。
mkdir -p "$WORK"

# ---- 1-9: snip -e 表达式求值（上游 test_cli.sh 逐条对应） ----
check_output "4" "$(expr_of '2 + 2')" "snip -e '2 + 2' → 4"
check_output "hello" "$(expr_of '"hello"')" "snip -e 字符串字面量 → hello"
check_output "2hello" "$(expr_of '"2" ++ "hello"')" "snip -e 字符串拼接 → 2hello"
check_output "hello" "$(expr_of '"hello\n"')" "snip -e 转义换行 → hello"
check_output "abc" "$(expr_of "['a', 'b', 'c']")" "snip -e 字符数组 → abc"
check_output "[1, 2, 3, 'a', 'b', 'c']" "$(expr_of "[1, 2, 3, 'a', 'b', 'c']")" "snip -e 混合数组 → 原样回显"
check_output "['a', 'b', 'c', 1, 2, 3]" "$(expr_of "['a', 'b', 'c', 1, 2, 3]")" "snip -e 混合数组2 → 原样回显"
check_output "abcd ++ [1, 2, 3]" "$(expr_of "['a', 'b', 'c', 'd', 1, 2, 3]")" "snip -e 拼接数组 → abcd ++ [1, 2, 3]"
check_output "[1, 2, 3, 4, 5]" "$(expr_of '[1..5]')" "snip -e 范围 [1..5] → 四格展开"

# ---- 10-13: Image_file → JPEG/PNG 保存（vips 编码链路 + 魔数） ----
IMG="$PREFIX/share/nip4/data/examples/businesscard/slanted_oval_vase2.jpg"
[ -f "$IMG" ] || IMG="$PREFIX/share/nip4/data/examples/framing/framing_picture.jpg"
mkdir -p "$WORK"

JPG="$WORK/out.jpg"
"$SNIP" -e "Image_file \"$IMG\"" -o "$JPG" >/dev/null 2>&1
if [ -f "$JPG" ] && [ -s "$JPG" ]; then
    ok "Image_file 保存 JPEG 存在且非空 ($(wc -c < "$JPG") bytes)"
else
    bad "Image_file 保存 JPEG 失败: $JPG 不存在或为空"
fi
MAGIC=$(dd if="$JPG" bs=1 count=3 2>/dev/null | od -An -tx1 | tr -d ' \n')
check_output "ffd8ff" "$MAGIC" "JPEG 魔数 ff d8 ff (真 JPEG)"

PNG="$WORK/out.png"
"$SNIP" -e "Image_file \"$IMG\"" -o "$PNG" >/dev/null 2>&1
if [ -f "$PNG" ] && [ -s "$PNG" ]; then
    ok "Image_file 保存 PNG 存在且非空 ($(wc -c < "$PNG") bytes)"
else
    bad "Image_file 保存 PNG 失败: $PNG 不存在或为空"
fi
MAGIC=$(dd if="$PNG" bs=1 count=4 2>/dev/null | od -An -tx1 | tr -d ' \n')
check_output "89504e47" "$MAGIC" "PNG 魔数 89 50 4e 47 (真 PNG)"

# ---- 14-17: OHOS 平台字节级检查（paml 先例同款，无 readelf 依赖） ----
elf_bytes() {
    # elf_bytes <offset> <count>
    od -An -tx1 -j "$1" -N "$2" "$SNIP" 2>/dev/null | tr -d ' \n'
}
check_output "7f454c46" "$(elf_bytes 0 4)" "ELF magic 7f 45 4c 46"
CLASS=$(elf_bytes 4 1)
[ "$CLASS" = "02" ] && ok "ELFCLASS64 (64-bit)" || bad "ELFCLASS 应为 02 (64-bit): $CLASS"
MACH=$(elf_bytes 18 2)
[ "$MACH" = "b700" ] && ok "e_machine EM_AARCH64 (b7 00)" || bad "e_machine 应为 aarch64: $MACH"

# 17: VIPSHOME 定位（Image_file 链路的前提，见脚本头部注释）
if [ "$VIPSHOME_IMPORT" = true ]; then
    ok "share/nip4/start 定位成功 (VIPSHOME=$PREFIX)"
else
    bad "share/nip4/start 未找到 (VIPSHOME 未注入, Image_file 断言 10-13 成立性存疑)"
fi

note ""
note "==== run_tests.sh: $PASS passed, $FAIL failed ===="
if [ -s "$WORK/expr.stderr" ]; then
    note "--- last snip -e stderr (diagnostic, non-fatal) ---"
    sed 's/^/  /' "$WORK/expr.stderr"
fi
[ "$FAIL" -eq 0 ]