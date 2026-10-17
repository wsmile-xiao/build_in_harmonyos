#!/bin/sh
# 消费者测试：以使用者身份运行打包后的 mksh，断言其可观察行为。
# 用法: test_mksh.sh <mksh 可执行文件>
# mksh 无 --version/--help 长选项（GNU 惯例不适用），上游标准取证入口是
#   `mksh -c 'echo $KSH_VERSION'` 与 `mksh -h`（合法旗标，空 stdin 下 rc=0）。
# 不启用 set -e：断言依赖失败命令的退出码（rc=$? 捕获），-e 会中断断言语义。
set -u

BIN="$1"

pass=0
fail=0

ok() {
    pass=$((pass + 1))
    printf 'PASS %s\n' "$1"
}

bad() {
    fail=$((fail + 1))
    printf 'FAIL %s\n' "$1"
    printf '     %s\n' "$2"
}

equals() { # 名称 期望 实际
    if [ "$2" = "$3" ]; then ok "$1"; else bad "$1" "expected=[$2] actual=[$3]"; fi
}

if [ ! -x "$BIN" ]; then
    printf 'FAIL binary-not-executable [%s]\n' "$BIN"
    exit 1
fi

# 1) 版本自报：KSH_VERSION 含 MIRBSD KSH R59（59c 即 R59 系列 bugfix 版）
ver=$("$BIN" -c 'echo $KSH_VERSION' 2>&1)
case "$ver" in
    *MIRBSD*KSH*R59*) ok "version-string" ;;
    *) bad "version-string" "actual=[$ver]" ;;
esac

# 2) -h 是合法调用旗标（hashall）：空 stdin 下必须 rc=0（顺证二进制可加载执行）
"$BIN" -h </dev/null >/dev/null 2>&1
equals "valid-flag-h-exit-code" "0" "$?"

# 3) 算术展开
equals "arithmetic-expansion" "42" "$("$BIN" -c 'echo $((6*7))' 2>&1)"

# 4) 变量赋值与花括号展开
equals "parameter-expansion" "abcdef" "$("$BIN" -c 'x=abc; y=${x}def; echo $y' 2>&1)"

# 5) 函数定义与调用（含位置参数）
equals "function-call" "ok-hi" "$("$BIN" -c 'f() { echo ok-$1; }; f hi' 2>&1)"

# 6) 管道执行
equals "pipeline" "data" "$(echo data | "$BIN" -c 'cat' 2>&1)"

# 7) 命令替换
equals "command-substitution" "sub" "$("$BIN" -c 'v=$(echo sub); echo $v' 2>&1)"

# 8) 退出码透传
"$BIN" -c 'exit 7' >/dev/null 2>&1
equals "exit-status" "7" "$?"

# 9) test/[] 内建与短路
equals "test-bracket-builtin" "yes" "$("$BIN" -c '[ 1 -lt 2 ] && echo yes' 2>&1)"

# 10) for 循环 + 重定向（3 行输出合并为分号串比较）
got=$("$BIN" -c 'for i in 1 2 3; do echo $i; done' 2>&1 | tr '\n' ';')
equals "loop-redirect" "1;2;3;" "$got"

printf 'mksh consumer tests: %d passed, %d failed\n' "$pass" "$fail"
[ "$fail" -eq 0 ] || exit 1
exit 0
