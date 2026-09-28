#!/bin/sh
# test_package/test_dash.sh — klibc-dash 适配后测试套件
#
# 由**被测包内的 bin/sh**（klibc 内嵌 dash）直接解释执行；启动器见 run_tests.sh。
# 用例分两组：
#   1) 通用 POSIX shell 行为（对照上游 dash 的功能面）
#   2) [OHOS-*] HarmonyOS 平台专有用例（/tmp 只读、pwd 内建兜底、签名 ELF 自我重执行）
#
# 退出码：全部通过（无 FAIL）返回 0，否则返回 1。

PASS=0
FAIL=0
SKIP=0

ok()   { echo "PASS   $1"; PASS=$((PASS + 1)); }
ng()   { echo "FAIL   $1 -- $2"; FAIL=$((FAIL + 1)); }
skip() { echo "SKIP   $1 -- $2"; SKIP=$((SKIP + 1)); }

check() { # name expected actual
	if [ "$2" = "$3" ]; then
		ok "$1"
	else
		ng "$1" "expected [$2] got [$3]"
	fi
}

SH_BIN="$1"          # 被测 bin/sh 的绝对路径（由 run_tests.sh 注入）
TMPD=${TMPDIR:-/tmp}

echo "== klibc-dash 适配后测试套件 =="
echo "被测 shell: $SH_BIN"
echo

# ---------- 1. 通用 POSIX shell 行为 ----------
check "printf-basic"          "hello"        "$(printf '%s' hello)"
check "arith-add"             "8"            "$((3 + 5))"
check "arith-hex"             "16"           "$((0x10))"
x=7; check "arith-var"        "42"           "$((x * 6))"

f() { printf '%s' "$1"; }
check "function-def"          "ok"           "$(f ok)"
g() { return 3; }
g; check "function-return"    "3"            "$?"

acc=""
for i in 1 2 3; do acc="$acc$i"; done
check "for-loop"              "123"          "$acc"

n=0; while [ "$n" -lt 4 ]; do n=$((n + 1)); done
check "while-loop"            "4"            "$n"

m=0; until [ "$m" -ge 2 ]; do m=$((m + 1)); done
check "until-loop"            "2"            "$m"

case "beta" in
alpha) c=A ;;
beta)  c=B ;;
*)     c=X ;;
esac
check "case-statement"        "B"            "$c"

if [ 1 -eq 2 ]; then r=no; elif [ 1 -eq 1 ]; then r=yes; else r=no; fi
check "if-elif-else"          "yes"          "$r"

v=world; check "var-quoting"  "hello world"  "$(printf 'hello %s' "$v")"
check "param-default"         "fallback"     "${unset_var:-fallback}"
w=abcde; check "param-length" "5"            "${#w}"
p=/a/b/c.sh
check "param-strip-dir"       "c.sh"         "${p##*/}"
check "param-strip-ext"       "/a/b/c"       "${p%.*}"
check "cmd-substitution"      "nested"       "$(printf '%s' "$(printf '%s' nested)")"

if command -v sort >/dev/null 2>&1 && command -v head >/dev/null 2>&1; then
	check "pipeline"      "a"            "$(printf 'b\na\n' | sort | head -1)"
else
	skip "pipeline"       "系统缺少 sort/head（外部命令）"
fi

check "exit-status-subshell"  "42"           "$( (exit 42); echo $? )"
sx=1; (sx=2); check "subshell-isolation" "1" "$sx"
check "test-builtin"          "y"            "$(if [ -n foo ]; then echo y; else echo n; fi)"
check "read-builtin"          "ab"           "$(printf 'ab\n' | { read line; printf '%s' "$line"; })"

rm -f "$TMPD/klibc-dash-t1" 2>/dev/null
printf 'redirected\n' > "$TMPD/klibc-dash-t1" 2>/dev/null
if [ -f "$TMPD/klibc-dash-t1" ]; then
	check "redirection-write-read" "redirected" "$(cat "$TMPD/klibc-dash-t1")"
	rm -f "$TMPD/klibc-dash-t1"
else
	skip "redirection-write-read" "无法在 $TMPD 写入"
fi

hd=$(cat <<EOF
heredoc-value
EOF
)
check "heredoc"               "heredoc-value" "$hd"
set -- one two
check "positional-set"        "one|two"      "$1|$2"

# ---------- 2. HarmonyOS 平台专有用例 ----------
# [OHOS-1] OHOS /tmp 只读（E002）：dash 及其构建期脚本必须走 $TMPDIR。
if [ -w "$TMPD" ]; then
	tf="$TMPD/klibc-dash-ohos-$$"
	printf 'ohos\n' > "$tf" 2>/dev/null
	if [ -s "$tf" ]; then ok "[OHOS-1] tmpdir-writable (TMPDIR=$TMPD)"; else ng "[OHOS-1] tmpdir-writable" "写入 $tf 失败"; fi
	rm -f "$tf"
else
	ng "[OHOS-1] tmpdir-writable" "$TMPD 不可写"
fi

# [OHOS-2] pwd 内建：dash 的 pwd 在 PWD 未设置时走目录 fd 兜底（上游 show.c 硬编码 /tmp），
#          验证在 OHOS 下不因 /tmp 只读而失效。
pwdout=$(cd / && pwd)
check "[OHOS-2] pwd-builtin-cwd" "/" "$pwdout"

# [OHOS-3] 代码签名 ELF 的自我重执行（E077）：被测 sh 再次 exec 自身执行 -c。
reexec=$("$SH_BIN" -c 'printf %s reexec-ok')
check "[OHOS-3] signed-elf-reexec" "reexec-ok" "$reexec"

echo
echo "== 结果: TOTAL=$((PASS + FAIL + SKIP)) PASS=$PASS FAIL=$FAIL SKIP=$SKIP =="
[ "$FAIL" -eq 0 ]
