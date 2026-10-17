#!/bin/sh
# test.sh — radamsa 0.7 功能性测试（8 项断言式检查）
# 用法: sh test.sh <radamsa-binary> <writable-workdir>
# 前 4 项为上游功能等价复验（tests/nop.sh 语义、种子确定性），后 4 项为
# 鸿蒙特有回归（字符设备 stdout 是 OHOS poll 缺陷的直接回归路径，见
# patches/0001-radamsa-do_poll-ohos-chardev-writable.patch）。
set -e

BIN="$1"
WORK="$2"
fail=0
i=0

check() {
    # check <描述> <退出码期望0与否的命令已执行> — 以 grep 为准的形式
    if [ "$1" = "ok" ]; then
        echo "ok - $2"
    else
        echo "FAIL - $2"
        fail=1
    fi
}

mkdir -p "$WORK"

# 1) --version 输出 Radamsa 0.7（上游功能）
"$BIN" --version > "$WORK/v.out" 2>&1
if grep -q "Radamsa 0.7" "$WORK/v.out"; then i=$((i+1)); check ok "--version 输出版本号 Radamsa 0.7"; else check no "--version 输出版本号"; fi

# 2) --about 自述（上游功能）
"$BIN" --about > "$WORK/a.out" 2>&1
if grep -q "general purpose fuzzer" "$WORK/a.out"; then i=$((i+1)); check ok "--about 含 general purpose fuzzer 自述"; else check no "--about 自述"; fi

# 3) 固定种子确定性：同种子两次输出逐字节一致（上游功能，fuzzer 核心语义）
printf 'The quick brown fox jumps over the lazy dog.\n' > "$WORK/sample.txt"
"$BIN" -s 42 -n 20 "$WORK/sample.txt" > "$WORK/det1.out" 2>"$WORK/det1.err"
"$BIN" -s 42 -n 20 "$WORK/sample.txt" > "$WORK/det2.out" 2>"$WORK/det2.err"
if cmp -s "$WORK/det1.out" "$WORK/det2.out"; then i=$((i+1)); check ok "固定种子 (-s 42) 输出逐字节确定"; else check no "固定种子确定性"; fi

# 4) -m nop -p od 恒等输出（上游 tests/nop.sh 语义）
echo "foo" | "$BIN" -m nop -p od > "$WORK/nop.out" 2>/dev/null
if grep -q "^foo$" "$WORK/nop.out"; then i=$((i+1)); check ok "-m nop -p od 恒等输出"; else check no "-m nop 恒等"; fi

# 5) 鸿蒙特有：stdout 重定向 /dev/null 完成（OHOS 字符设备 poll 缺陷回归；
#    未打补丁时进程在 select() 无限等待中挂死，见 patches/0001）
rc=0
"$BIN" -s 42 -n 100 "$WORK/sample.txt" > /dev/null 2>"$WORK/devnull.err" || rc=$?
if [ "$rc" -eq 0 ]; then i=$((i+1)); check ok "鸿蒙特有: stdout>/dev/null 完成不挂起（字符设备 poll 回归）"; else check no "stdout>/dev/null 回归 (rc=$rc)"; fi

# 6) 鸿蒙特有：stdout 重定向 /dev/zero 完成（同上，字符设备族覆盖）
rc=0
"$BIN" -s 42 -n 100 "$WORK/sample.txt" > /dev/zero 2>"$WORK/devzero.err" || rc=$?
if [ "$rc" -eq 0 ]; then i=$((i+1)); check ok "鸿蒙特有: stdout>/dev/zero 完成不挂起"; else check no "stdout>/dev/zero 回归 (rc=$rc)"; fi

# 7) 鸿蒙特有：产物文件落到 HMFS 可写目录（build 目录），%n 序号展开生成 n 个文件
"$BIN" -s 42 -n 3 -o "$WORK/fz-%n" "$WORK/sample.txt" > /dev/null 2>&1
n=$(ls "$WORK"/fz-* 2>/dev/null | wc -l)
if [ "$n" -eq 3 ]; then i=$((i+1)); check ok "鸿蒙特有: -o HMFS 路径 %n 展开生成 3 个输出文件"; else check no "-o %n 生成文件数 (got $n)"; fi

# 8) 鸿蒙特有：stdin 管道进出（cat | radamsa | 下游消费 的标准管线上下游形态）
printf 'HAL 9000\n' | "$BIN" -s 7 -n 5 2>/dev/null | wc -c > "$WORK/pipe.cnt"
c=$(cat "$WORK/pipe.cnt")
if [ "$c" -gt 0 ]; then i=$((i+1)); check ok "鸿蒙特有: stdin 管道输入 + stdout 管道输出 ($c 字节)"; else check no "管道形态输出为空"; fi

echo "assertions_run=$i"
if [ "$fail" -ne 0 ]; then
    exit 1
fi
exit 0
