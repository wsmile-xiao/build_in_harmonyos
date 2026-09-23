#!/bin/sh
# test.sh — neatvi 19 功能性测试（6 项断言式检查）
# 用法: sh test.sh <vi-binary> <stag-binary> <writable-workdir>
# vi 以 ex 模式（-s -e）从 stdin 读命令流（上游 test.sh 同模式）；
# 工作目录切换到可写 workdir（HMFS /tmp 只读，here-doc 临时文件须
# TMPDIR 重定向——由 test_package conanfile 传入）。
set -e

VI="$1"
STAG="$2"
WORK="$3"
fail=0

check() {
    # check <描述> <文件> <grep 模式>
    if grep -q "$3" "$2"; then
        echo "ok - $1"
    else
        echo "FAIL - $1"
        fail=1
    fi
}

cd "$WORK"

# 1) ex 模式插入文本并写盘
printf 'i\nhello neatvi ohos\n.\n:w t1.txt\n:q\n' | "$VI" -s -e >/dev/null 2>&1
check "ex 插入并写盘" t1.txt "hello neatvi ohos"

# 2) ex 全局替换（:%s）
printf ':%%s/neatvi/OHOS PC/\n:w t2.txt\n:q\n' | "$VI" -s -e t1.txt >/dev/null 2>&1
check "ex :%%s 全局替换" t2.txt "hello OHOS PC ohos"

# 3) UTF-8 中文编辑（neatvi 主打特性）
printf ':1s/OHOS/鸿蒙/\n:w t3.txt\n:q\n' | "$VI" -s -e t2.txt >/dev/null 2>&1
check "UTF-8 中文替换" t3.txt "鸿蒙"

# 4) stag 生成 tags（C 函数定义识别）
# stag 的 C 模式要求函数定义行不含 { 或 ; 且行尾紧贴参数列表
# （^[a-zA-Z_][^{;]*\<name\([^;]+(//.*|/\*.*)?$），单行带函数体
# （int main(void) { return 0; }）不在其启发式覆盖范围 → 用 K&R 多行式。
cat > t4.c <<'EOF'
int main(void)
{
	return 0;
}
EOF
"$STAG" t4.c > tags.out 2>/dev/null || true
check "stag 生成 tags 含 main" tags.out "main"

# 5) 鸿蒙特有：无控制终端的窗口几何回退路径。
#    term.c:21 的 tcgetattr(0,...) 不检查返回值、无 isatty 门控；term.c:31
#    的 ioctl(0,TIOCGWINSZ) 在 stdin 为管道时必然失败，于是 rows/cols 只能
#    取自 $LINES/$COLUMNS、再退化为 80x25。OHOS CI/HMFS 无 tty，这条回退
#    分支就是实际生效路径。term_done() 以 term_pos(rows-1,0) 收尾，其发出的
#    绝对定位序列 ESC[<rows>;1H 可直接断言 rows 来自 $LINES=13。
#    上游 test/v??.sh 全部 `./vi -v >/dev/null`，从不检查终端几何，无此判据。
ESC=$(printf '\033')
printf ':q\n' | LINES=13 COLUMNS=77 "$VI" -v > v.out 2>/dev/null || true
check "鸿蒙特有：无 tty 下几何回退 \$LINES=13（ESC[13;1H）" \
      v.out "${ESC}\\[13;1H"

# 6) 鸿蒙特有：视觉/行编辑两种模式在 stdin 为管道、无 tty 下均以退出码 0 结束。
#    term_init/term_done 对 tcgetattr/tcsetattr 的返回值不检查，bionic 上
#    ENOTTY 不得导致中止（$LINES/$COLUMNS/$TERM 均清空以走 80x25 默认分支）；
#    上游 v??.sh 用管道驱动但不看退出码（其结果只靠 cmp 文件内容判定），
#    退出码判据为本次适配新增。
set +e
printf ':q\n' | ( unset LINES COLUMNS TERM; "$VI" -v ) > v2.out 2>&1
rc_v=$?
printf ':q\n' | "$VI" -s -e > e2.out 2>&1
rc_e=$?
set -e
if [ "$rc_v" -eq 0 ] && [ "$rc_e" -eq 0 ]; then
    echo "ok - 鸿蒙特有：无 tty 下 -v/-s -e 均退出码 0"
else
    echo "FAIL - 鸿蒙特有：无 tty 下退出码应为 0（-v: $rc_v, -e: $rc_e）"
    fail=1
fi

if [ "$fail" -ne 0 ]; then
    echo "neatvi test_package: FAILED"
    exit 1
fi
echo "neatvi test_package: all 6 checks passed"
