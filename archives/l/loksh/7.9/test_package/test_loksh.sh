#!/bin/bash
# 消费者测试 — loksh 7.9（上游无测试套件，按赛事规则自补）
# 用法: test_loksh.sh <包内 ksh 绝对路径>
# 12 项断言，全部离线，真实执行被适配工具（R34）。
set -u
KSH="$1"
TMP="$(mktemp -d)" || exit 1
trap 'rm -rf "$TMP"' EXIT
PASS=0
FAIL=0

check() { # check <描述> <期望输出> <实际输出>
  if [ "$2" = "$3" ]; then
    PASS=$((PASS+1))
    echo "ok $PASS - $1"
  else
    FAIL=$((FAIL+1))
    echo "FAIL - $1: expected [$2] got [$3]"
  fi
}

# 1. 基本执行
check "echo 基本执行" "ok" "$("$KSH" -c 'echo ok' 2>&1)"

# 2. 变量与算术展开
check "变量与 \$(( )) 算术" "42" "$("$KSH" -c 'x=41; echo $((x+1))' 2>&1)"

# 3. for 循环 + printf
check "for 循环 + printf" "1,2,3," "$("$KSH" -c 'for i in 1 2 3; do printf "%s," $i; done' 2>&1)"

# 4. 管道
check "管道 echo|tr" "HELLO" "$("$KSH" -c 'echo hello | tr a-z A-Z' 2>&1)"

# 5. 退出码传递
"$KSH" -c 'exit 7' >/dev/null 2>&1
check "退出码 exit 7 -> \$?" "7" "$?"

# 6. 脚本文件执行
printf 'echo from-script\n' > "$TMP/s.ksh"
check "脚本文件执行" "from-script" "$("$KSH" "$TMP/s.ksh" 2>&1)"

# 7. 位置参数（-c 后第一个参数是 $0，其后才是 $1..$n）
check "位置参数 \$#" "3" "$("$KSH" -c 'echo $#' dummy a b c 2>&1)"

# 8. test 内建
check "[ ] test 内建" "yes" "$("$KSH" -c '[ 1 -lt 2 ] && echo yes' 2>&1)"

# 9. 子 shell
check "子 shell ( )" "sub" "$("$KSH" -c '(echo sub)' 2>&1)"

# 10. while read 读 here-doc
check "while read here-doc" "a,b,c," "$("$KSH" -c 'while read w; do printf "%s," $w; done <<EOF
a
b
c
EOF
echo' 2>&1)"

# 11. 函数定义与调用
check "函数定义与调用" "fn" "$("$KSH" -c 'f(){ echo fn; }; f' 2>&1)"

# 12. KSH_VERSION 非空
V="$("$KSH" -c 'echo ${KSH_VERSION}' 2>&1)"
if [ -n "$V" ]; then
  PASS=$((PASS+1)); echo "ok $PASS - KSH_VERSION 非空 [$V]"
else
  FAIL=$((FAIL+1)); echo "FAIL - KSH_VERSION 为空"
fi

echo "----------------------------------------"
echo "总结: 通过 $PASS / $((PASS+FAIL)), 失败 $FAIL"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
