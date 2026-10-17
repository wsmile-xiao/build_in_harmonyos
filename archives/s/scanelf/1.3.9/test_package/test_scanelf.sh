#!/bin/sh
# scanelf/1.3.9 — 消费者用例（conan test_package）
#
# 用法: sh test_scanelf.sh <package bin dir> <package folder>
#
# 这一层扮演真实消费者：只用「已安装产物」跑工具本身，验证交付物不是编译通过即算数的空壳。
# 上游官方套件（-Dtests=true 注册的 6 条 meson test，含 tests/scanelf 的 golden 比对）在
# conanfile.py build() 里实跑；本脚本补上游没覆盖的角度：
#   * 消费者实际拿到的包里有什么：按工具拆包的隔离性 + 许可证交付；
#   * 上游 golden 语义在「安装后的二进制」上是否成立（上游测的是 builddir 里的产物）；
#   * 鸿蒙特有场景：musl 运行时（NEEDED 是 libc.so 而非 glibc 的 libc.so.6），以及用
#     运行期从 /proc/self/maps 解析出来的真实系统 musl libc 做 ELF 解析——路径不写死，
#     真机与 CI 同样成立。
#
# 断言 15 条（与 test_package/MANIFEST.yml 的 assertion_count 对齐）
set -u

BINDIR=${1:?usage: test_scanelf.sh <package bin dir> <package folder>}
PKGDIR=${2:?usage: test_scanelf.sh <package bin dir> <package folder>}
SCANELF="$BINDIR/scanelf"

OUT="./.scanelf-test.out.$$"
ERR="./.scanelf-test.err.$$"
NONELF="./.scanelf-test.nonelf.$$"
cleanup() { rm -f "$OUT" "$ERR" "$NONELF"; }
trap cleanup EXIT INT TERM

pass=0
fail=0
ok() { echo "PASS: $1"; pass=$((pass + 1)); }
no() { echo "FAIL: $1"; fail=$((fail + 1)); }
# 运行工具：stdout/stderr 落文件，退出码经 $? 交给调用方
run() { "$@" >"$OUT" 2>"$ERR"; return $?; }

# 非 ELF 输入（负向对照用），放在当前构建目录并随 EXIT trap 删除
printf 'this file is deliberately not an ELF object\n' >"$NONELF"

echo "== scanelf/1.3.9 consumer test =="
echo "package bin dir : $BINDIR"
echo "package folder  : $PKGDIR"

# --- 1. 交付物存在且可执行 -------------------------------------------------
if [ -x "$SCANELF" ]; then
	ok "bin/scanelf 已安装且可执行"
else
	no "bin/scanelf 缺失或不可执行: $SCANELF"
fi

# --- 2. 按工具拆包：同一源码树的其他工具不得夹带 --------------------------
stray=""
for t in dumpelf pspax scanmacho lddtree symtree; do
	if [ -e "$BINDIR/$t" ]; then
		stray="$stray $t"
	fi
done
if [ -z "$stray" ]; then
	ok "本包只交付 scanelf（未夹带 dumpelf/pspax/scanmacho/lddtree/symtree）"
else
	no "本包夹带了其他工具:$stray"
fi

# --- 3. 许可证交付（GPL-2.0-only）-----------------------------------------
if [ -f "$PKGDIR/licenses/COPYING" ]; then
	ok "licenses/COPYING 已交付"
else
	no "licenses/COPYING 缺失: $PKGDIR/licenses/COPYING"
fi

# --- 4. 版本自证 ----------------------------------------------------------
run "$SCANELF" -V
rc=$?
if [ "$rc" -eq 0 ] && grep -q "pax-utils-1.3.9" "$OUT" && grep -q "1.3.9" "$OUT"; then
	ok "-V 自证上游版本 (pax-utils-1.3.9)"
else
	no "-V 未自证版本 (rc=$rc, out=$(tr '\n' '|' <"$OUT"))"
fi

# --- 5. 上游 golden 语义，作用于「安装后的二进制」 ------------------------
run "$SCANELF" -qsmain -F'%s %f' "$SCANELF"
rc=$?
if [ "$rc" -eq 0 ] && [ "$(cat "$OUT")" = "main scanelf" ]; then
	ok "符号查找与格式串: -qsmain -F'%s %f' 输出恰为 \"main scanelf\"（上游 tests/scanelf golden 语义）"
else
	no "符号查找输出不符 (rc=$rc, out=$(tr '\n' '|' <"$OUT"), err=$(tr '\n' '|' <"$ERR"))"
fi

# --- 6. [OHOS] musl 运行时：NEEDED 是 libc.so，不是 glibc 的 libc.so.6 ----
run "$SCANELF" -n "$SCANELF"
rc=$?
if [ "$rc" -eq 0 ] && grep -q "libc\.so" "$OUT" && ! grep -q "libc\.so\.6" "$OUT"; then
	ok "[OHOS] -n 报出 musl 运行时 libc.so（且无 glibc 的 libc.so.6）"
else
	no "[OHOS] NEEDED 列不符 (rc=$rc, out=$(tr '\n' '|' <"$OUT"))"
fi

# --- 7. [OHOS] 运行期解析真实系统 musl C 库（不写死路径）------------------
# OHOS 的 musl 把 libc 与动态加载器做成同一个文件（ld-musl-aarch64.so.1），进程
# maps 里因此没有 libc.so 条目：先找 ld-musl-*，再退到 libc.so*。
SYSLIBC=""
for pat in 'ld-musl-[^ ]*\.so[^ ]*' 'libc\.so[^ ]*'; do
	[ -n "$SYSLIBC" ] && break
	SYSLIBC=$(grep -oE "/[^ ]*$pat" /proc/self/maps 2>/dev/null | sed -n '1p')
done
if [ -n "$SYSLIBC" ] && [ -e "$SYSLIBC" ]; then
	ok "[OHOS] 从 /proc/self/maps 解析出运行中的系统 musl C 库: $SYSLIBC"
else
	no "[OHOS] 未能从 /proc/self/maps 解析出系统 musl C 库"
fi

# --- 8. [OHOS] 扫描真实系统 libc：NEEDED 视图 -----------------------------
if [ -n "$SYSLIBC" ] && [ -e "$SYSLIBC" ]; then
	run "$SCANELF" -n "$SYSLIBC"
	rc=$?
	if [ "$rc" -eq 0 ] && grep -q "ET_DYN" "$OUT"; then
		ok "[OHOS] -n 解析 OHOS 系统 musl libc 成功 (ET_DYN)"
	else
		no "[OHOS] -n 解析系统 musl libc 失败 (rc=$rc, out=$(tr '\n' '|' <"$OUT"))"
	fi
else
	no "[OHOS] 跳过：系统 musl libc 路径不可用"
fi

# --- 9. [OHOS] 扫描真实系统 libc：ELF 头视图 ------------------------------
if [ -n "$SYSLIBC" ] && [ -e "$SYSLIBC" ]; then
	run "$SCANELF" -e "$SYSLIBC"
	rc=$?
	if [ "$rc" -eq 0 ] && grep -q "ET_DYN" "$OUT"; then
		ok "[OHOS] -e 解出 OHOS 系统 musl libc 的 ELF 头 (ET_DYN)"
	else
		no "[OHOS] -e 解析系统 musl libc 失败 (rc=$rc, out=$(tr '\n' '|' <"$OUT"))"
	fi
else
	no "[OHOS] 跳过：系统 musl libc 路径不可用"
fi

# --- 10. 多文件 + 自定义格式串 -------------------------------------------
run "$SCANELF" -q -F'%f %n' "$SCANELF" "$SCANELF"
rc=$?
lines=$(wc -l <"$OUT" | tr -d ' ')
if [ "$rc" -eq 0 ] && [ "$lines" = "2" ] && grep -q "^scanelf " "$OUT"; then
	ok "-q -F'%f %n' 多文件输入逐行输出 (2 行)"
else
	no "多文件格式输出不符 (rc=$rc, lines=$lines, out=$(tr '\n' '|' <"$OUT"))"
fi

# --- 11. OSABI 视图（-I）可用 -------------------------------------------
run "$SCANELF" -I "$SCANELF"
rc=$?
if [ "$rc" -eq 0 ] && grep -q "OSABI" "$OUT" && grep -q "ET_DYN" "$OUT"; then
	ok "-I OSABI 视图可用（表头 OSABI + ET_DYN）"
else
	no "-I OSABI 视图不符 (rc=$rc, out=$(tr '\n' '|' <"$OUT"))"
fi

# --- 12. [OHOS] INTERP 指向 musl 加载器 ---------------------------------
run "$SCANELF" -i "$SCANELF"
rc=$?
interp=$(sed -n '2p' "$OUT")
if [ "$rc" -eq 0 ] && grep -q "INTERP" "$OUT" && grep -q "musl" "$OUT"; then
	ok "[OHOS] -i 解出 INTERP 指向 musl 加载器: $interp"
else
	no "[OHOS] -i INTERP 不符 (rc=$rc, out=$(tr '\n' '|' <"$OUT"))"
fi

# --- 13. 负向对照：非 ELF 输入不得产出符号匹配 ---------------------------
run "$SCANELF" -qsmain -F'%s %f' "$NONELF"
if ! grep -q "main" "$OUT"; then
	ok "负向: 非 ELF 输入不产出符号匹配（防假绿）"
else
	no "负向: 非 ELF 输入竟产出符号匹配: $(tr '\n' '|' <"$OUT")"
fi

# --- 14. 负向对照：非 ELF 输入不得解出 ELF 类型 --------------------------
run "$SCANELF" -e "$NONELF"
if ! grep -qE "ET_DYN|ET_EXEC" "$OUT"; then
	ok "负向: 非 ELF 输入不解出 ET_DYN/ET_EXEC（防假绿）"
else
	no "负向: 非 ELF 输入竟解出 ELF 类型: $(tr '\n' '|' <"$OUT")"
fi

# --- 15. 解析分支未被裁剪：类型视图可用 ---------------------------------
run "$SCANELF" -t "$SCANELF"
rc=$?
if [ "$rc" -eq 0 ] && grep -q "ET_DYN" "$OUT"; then
	ok "-t 类型视图可用 (ET_DYN)"
else
	no "-t 类型视图失败 (rc=$rc, out=$(tr '\n' '|' <"$OUT"))"
fi

echo "--------------------------------------"
echo "PASS: $pass  FAIL: $fail  (total $((pass + fail)))"
if [ "$fail" -ne 0 ]; then
	echo "consumer test FAILED"
	exit 1
fi
echo "consumer test OK"
exit 0
