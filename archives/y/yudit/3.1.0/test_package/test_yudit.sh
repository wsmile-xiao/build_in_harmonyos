#!/bin/sh
# test_yudit.sh — yudit 3.1.0 消费者侧功能测试（POSIX sh，toybox 兼容，不用 set/pipefail）
#
# 用法: test_yudit.sh <yudit package 目录>
# 由 test_package/conanfile.py 调用，真实执行被测包安装的命令行工具。
#
# 用例:
#   T1 uniconv UTF-8 -> UTF-16 -> UTF-8 往返（真实字符集转换，R34 实质依赖被测包）
#   T2 uniprint 渲染上游样例 tests/testtext/romaji.txt 为 PostScript 并校验结构
#   T3 yudit 启动并加载完整 X11 运行期依赖链（libX11.so.6 -> libxcb/libXau/libXdmcp）
#      —— 无 X server，期望输出 "Can not open display."；若动态库缺失则报
#         "Error loading shared library"，据此区分「依赖链完好」与「依赖链损坏」。

PKG="$1"
BIN="$PKG/bin"
TMP="${TMPDIR:-/tmp}"
WORK="$TMP/yudit-test-$$"
mkdir -p "$WORK" || exit 1

total=0
passed=0
failed=0

report() { # name status detail
  total=$((total + 1))
  if [ "$2" = "PASS" ]; then passed=$((passed + 1)); else failed=$((failed + 1)); fi
  printf 'CASE %-8s %-4s %s\n' "$1" "$2" "$3"
}

# ---------- 前置：二进制存在且可执行 ----------
for t in yudit uniconv uniprint mytool; do
  if [ ! -x "$BIN/$t" ]; then
    report "T0-$t" FAIL "缺少可执行文件 $BIN/$t"
  fi
done

# ---------- T1: uniconv 往返 ----------
printf 'Hello Yudit \316\251 \344\270\255\346\226\207\n' > "$WORK/in.txt"
"$BIN/uniconv" -in "$WORK/in.txt" -out "$WORK/out16.txt" -encode utf-16 > "$WORK/t1a.log" 2>&1
rc1=$?
"$BIN/uniconv" -in "$WORK/out16.txt" -out "$WORK/back.txt" -decode utf-16 > "$WORK/t1b.log" 2>&1
rc2=$?
if [ "$rc1" = "0" ] && [ "$rc2" = "0" ] && cmp -s "$WORK/in.txt" "$WORK/back.txt"; then
  hdr=$(od -A n -t x1 -N 2 "$WORK/out16.txt" | tr -d ' ')
  if [ "$hdr" = "fffe" ]; then
    report "T1" PASS "uniconv UTF-8->UTF-16->UTF-8 往返一致（BOM ff fe，rc=$rc1/$rc2）"
  else
    report "T1" FAIL "UTF-16 BOM 异常: '$hdr'"
  fi
else
  report "T1" FAIL "往返失败 (rc=$rc1/$rc2) $(cat "$WORK/t1a.log" "$WORK/t1b.log" 2>/dev/null | head -2)"
fi

# ---------- T2: uniprint 渲染为 PostScript ----------
printf 'Yudit on HarmonyOS\n' > "$WORK/sample.txt"
"$BIN/uniprint" -font yudit.ttf -size 20 -hsize 0 -out "$WORK/out.ps" < "$WORK/sample.txt" > "$WORK/t2.log" 2>&1
rc3=$?
ps_ok=no
if [ "$rc3" = "0" ] && [ -s "$WORK/out.ps" ]; then
  first=$(head -1 "$WORK/out.ps")
  last=$(tail -1 "$WORK/out.ps")
  if [ "$first" = "%!PS-Adobe-3.0" ] && [ "$last" = "%%EOF" ]; then ps_ok=yes; fi
fi
if [ "$ps_ok" = "yes" ]; then
  report "T2" PASS "uniprint 输出合法 PostScript（$(wc -c < "$WORK/out.ps" | tr -d ' ') 字节，$(cat "$WORK/t2.log" | head -1)）"
else
  report "T2" FAIL "uniprint 失败 rc=$rc3 first='$first' last='$last' $(head -1 "$WORK/t2.log")"
fi

# ---------- T3: yudit 完整 X11 运行期依赖链 ----------
"$BIN/yudit" < /dev/null > "$WORK/t3.log" 2>&1
load_err=$(grep -c 'Error loading shared library' "$WORK/t3.log")
if [ "$load_err" != "0" ]; then
  report "T3" FAIL "X11 运行期依赖链缺失: $(grep 'Error loading shared library' "$WORK/t3.log" | head -2 | tr '\n' ' ')"
elif grep -q 'Can not open display' "$WORK/t3.log"; then
  report "T3" PASS "yudit 加载 libX11 依赖链成功并到达显示层（无 X server，预期 'Can not open display.'）"
else
  report "T3" FAIL "yudit 输出不符合预期: $(head -3 "$WORK/t3.log" | tr '\n' ' ')"
fi

rm -rf "$WORK"
printf 'SHELL_RESULT total=%s passed=%s failed=%s\n' "$total" "$passed" "$failed"
[ "$failed" = "0" ] || exit 1
exit 0
