#!/bin/sh
# quicklisp/20150128 test_package 测试脚本（消费者视角 L1，POSIX sh）
#
# 用法: sh test.sh <quicklisp_pkg_folder> <ecl_pkg_folder>
#
# 上游 quicklisp-bootstrap 没有自动化测试套件（Makefile 只有 all:/tag: 两个目标），
# 上游唯一的"功能入口"就是 README.txt 所述：(load "quicklisp.lisp")。因此本脚本：
#   * 用例 1 pkg-layout        制品完整性（文件、大小、sha256）
#   * 用例 2 lisp-content      上游启动文件内容标记 + S-表达式结构自检
#   * 用例 3 ohos-env-helper   OHOS 运行期环境契约（鸿蒙特有改动）
#   * 用例 4 ohos-ecl-load     OHOS/armv8 上用 ECL 实际 (load quicklisp.lisp)（鸿蒙特有）
set -u

PKG="${1:?usage: test.sh <quicklisp_pkg_folder> <ecl_pkg_folder>}"
ECL_PKG="${2:?usage: test.sh <quicklisp_pkg_folder> <ecl_pkg_folder>}"
SHARE="$PKG/share/quicklisp"
LISP="$SHARE/quicklisp.lisp"
HELPER="$SHARE/quicklisp-ohos-env.sh"

TOTAL=0; PASSED=0; FAILED=0; SKIPPED=0
pass() { TOTAL=$((TOTAL+1)); PASSED=$((PASSED+1)); echo "CASE $1 ... PASS ($2)"; }
fail() { TOTAL=$((TOTAL+1)); FAILED=$((FAILED+1)); echo "CASE $1 ... FAIL ($2)"; }
skip() { TOTAL=$((TOTAL+1)); SKIPPED=$((SKIPPED+1)); echo "CASE $1 ... SKIP ($2)"; }

echo "=== quicklisp test_package @ $(uname -s) $(uname -m) ==="

# ── 用例 1: pkg-layout ────────────────────────────────────────────────
c1="ok"
[ -f "$LISP" ]                 || c1="quicklisp.lisp missing: $LISP"
[ -f "$SHARE/README.txt" ]     || c1="${c1};README.txt missing"
[ -f "$PKG/licenses/LICENSE.txt" ] || c1="${c1};licenses/LICENSE.txt missing"
if [ -f "$LISP" ]; then
  size=$(wc -c < "$LISP" | tr -d ' ')
  [ "$size" = "57144" ] || c1="${c1};size=$size != 57144"
  if command -v sha256sum >/dev/null 2>&1; then
    sum=$(sha256sum "$LISP" | cut -d' ' -f1)
    [ "$sum" = "4a7a5c2aebe0716417047854267397e24a44d0cce096127411e9ce9ccfeb2c17" ] \
      || c1="${c1};sha256=$sum"
  fi
fi
[ "$c1" = "ok" ] \
  && pass pkg-layout "quicklisp.lisp 57144B + README.txt + LICENSE.txt，sha256 与上游一致" \
  || fail pkg-layout "$c1"

# ── 用例 2: lisp-content ─────────────────────────────────────────────
c2="ok"
for m in 'qlqs-info:*version* "2015-01-28"' \
         '(defun install' \
         '(defpackage #:qlqs-http' \
         '(defpackage #:qlqs-minitar' \
         '(defun unpack-tarball' ; do
  grep -qF "$m" "$LISP" || c2="${c2};missing marker: $m"
done
if command -v python3 >/dev/null 2>&1; then
  python3 - "$LISP" <<'PY' || c2="${c2};S-expression 括号不平衡/截断"
import sys

s = open(sys.argv[1], encoding="utf-8", errors="replace").read()
d = 0; i = 0; n = len(s)
while i < n:
    if s.startswith("#|", i):              # 块注释（可嵌套）
        depth = 1; i += 2
        while i < n and depth:
            if s.startswith("#|", i): depth += 1; i += 2
            elif s.startswith("|#", i): depth -= 1; i += 2
            else: i += 1
        continue
    c = s[i]
    if c == '"':                           # 字符串
        i += 1
        while i < n:
            if s[i] == "\\": i += 2; continue
            if s[i] == '"': i += 1; break
            i += 1
        continue
    if s.startswith("#\\", i):             # 字符字面量：#\; / #\( / #\Space
        i += 2
        if i < n:
            if s[i].isalpha():
                while i < n and (s[i].isalnum() or s[i] == "-"): i += 1
            else:
                i += 1
        continue
    if c == ";":                           # 行注释
        while i < n and s[i] != "\n": i += 1
        continue
    if c == "(":
        d += 1
    elif s.startswith("#(", i):            # 向量字面量 #(...)
        d += 1; i += 2; continue
    elif c == ")":
        d -= 1
        if d < 0: sys.exit(1)
    i += 1
sys.exit(0 if d == 0 else 1)
PY
fi
[ "$c2" = "ok" ] \
  && pass lisp-content "版本/安装入口/HTTP 客户端/minitar 标记齐全，S-表达式平衡" \
  || fail lisp-content "$c2"

# ── 用例 3: ohos-env-helper（鸿蒙特有）──────────────────────────────
c3="ok"
[ -f "$HELPER" ] || c3="helper missing: $HELPER"
if [ "$c3" = "ok" ]; then
  # HOME 已设置 → QUICKLISP_HOME = $HOME/quicklisp
  out1=$(QUICKLISP_BOOTSTRAP="$LISP" HOME=/storage/Users/currentUser \
         sh -c '. "$1"; printf "%s|%s" "$QUICKLISP_BOOTSTRAP" "$QUICKLISP_HOME"' _ "$HELPER")
  [ "$out1" = "$LISP|/storage/Users/currentUser/quicklisp" ] || c3="HOME set -> $out1"
  # HOME 未设置（模拟 OHOS 沙箱进程）→ 回退到 OHOS 默认用户目录
  out2=$(QUICKLISP_BOOTSTRAP="$LISP" \
         sh -c 'unset HOME; . "$1"; printf "%s|%s" "$QUICKLISP_BOOTSTRAP" "$QUICKLISP_HOME"' _ "$HELPER")
  [ "$out2" = "$LISP|/storage/Users/currentUser/quicklisp" ] || c3="${c3};HOME unset -> $out2"
  [ -r "$LISP" ] || c3="${c3};bootstrap not readable"
fi
[ "$c3" = "ok" ] \
  && pass ohos-env-helper "QUICKLISP_BOOTSTRAP 可解析；QUICKLISP_HOME 在 HOME 缺失时回退 /storage/Users/currentUser/quicklisp" \
  || fail ohos-env-helper "$c3"

# ── 用例 4: ohos-ecl-load（鸿蒙特有）────────────────────────────────
c4="ok"
if ! command -v ecl >/dev/null 2>&1; then
  skip ohos-ecl-load "ecl 不在 PATH 上（runenv 未提供语言运行时）"
else
  # ECL 的 (require ...) 在 *load-path* + 当前目录查找模块；ohpcd 的 ecl 包
  # 以 prefix=/ 构建 → *load-path* 为空，必须在模块目录下运行，
  # 否则 quicklisp.lisp 的 ECL 分支 (:prep (require 'sockets)) 会失败。
  ECL_LIB=""
  for d in "$ECL_PKG"/lib/ecl-*; do [ -d "$d" ] && ECL_LIB="$d"; done
  if [ -z "$ECL_LIB" ] || [ ! -f "$ECL_LIB/sockets.fas" ]; then
    skip ohos-ecl-load "ecl 模块目录/sockets.fas 未找到（$ECL_PKG/lib）"
  else
    out=$(cd "$ECL_LIB" && ecl -norc \
        -eval "(load \"$LISP\")" \
        -eval '(format t "~&QLQS_VERSION=~A~%" qlqs-info:*version*)' \
        -eval '(format t "~&QUICKSTART_INSTALL=~A~%" (if (fboundp (find-symbol "INSTALL" "QUICKLISP-QUICKSTART")) "present" "missing"))' \
        -eval '(quit)' 2>&1)
    echo "$out" | grep -q 'quicklisp quickstart 2015-01-28 loaded' || c4="load 横幅缺失"
    echo "$out" | grep -q 'QLQS_VERSION=2015-01-28'                  || c4="${c4};版本号不符"
    echo "$out" | grep -q 'QUICKSTART_INSTALL=present'               || c4="${c4};install 入口缺失"
    if [ "$c4" != "ok" ]; then
      echo "$out" | sed 's/^/    | /'
    else
      echo "$out" | grep -E 'quicklisp quickstart|QLQS_VERSION|QUICKSTART_INSTALL' | sed 's/^/    | /'
    fi
    [ "$c4" = "ok" ] \
      && pass ohos-ecl-load "ECL 24.5.10(OHOS/armv8) 实际 (load quicklisp.lisp) 成功，版本 2015-01-28" \
      || fail ohos-ecl-load "$c4"
  fi
fi

echo "SUMMARY total=$TOTAL passed=$PASSED failed=$FAILED skipped=$SKIPPED"
[ "$FAILED" -eq 0 ]
