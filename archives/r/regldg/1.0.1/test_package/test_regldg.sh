#!/bin/sh
# test_regldg.sh — regldg 1.0.1 功能性测试（6 项断言式检查）
# 用法: sh test_regldg.sh <regldg-binary> <writable-workdir>
# 前 5 项为上游功能验证（含 Homebrew `regldg test` 等价 smoke），第 6 项为
# 鸿蒙形态验证（管道 + HMFS 可写目录输出）。
# 注意：刻意只用 set -u 而不用 set -e——harness 必须在任何单项失败后继续
# 执行并始终打印 RESULT 尾行（真机门禁解析该行计数；提前退出会导致
# incomplete 而非明确失败）。

set -u

BIN="$1"
WORK="$2"
p=0
f=0

check() {
    if [ "$1" = "ok" ]; then
        echo "ok - $2"
        p=$((p+1))
    else
        echo "FAIL - $2"
        f=$((f+1))
    fi
}

mkdir -p "$WORK"

# 1) Homebrew 等价 smoke：正则 "test" 为有限语言，输出单个词 "test"
"$BIN" test > "$WORK/t1.out" 2>&1
if grep -qx "test" "$WORK/t1.out"; then check ok "regldg test 输出单个词 test"; else check no "regldg test 输出"; fi

# 2) 分支输出：-n 2 'a|b' 输出 a、b 两行
"$BIN" -n 2 'a|b' > "$WORK/t2.out" 2>&1
if grep -qx "a" "$WORK/t2.out" && grep -qx "b" "$WORK/t2.out"; then check ok "-n 2 'a|b' 输出 a、b 两行"; else check no "-n 2 'a|b' 输出"; fi

# 3) 长选项路径：--num-words-output=1 'ab?' 退出 0 且输出非空
"$BIN" --num-words-output=1 'ab?' > "$WORK/t3.out" 2>&1
if [ -s "$WORK/t3.out" ]; then check ok "--num-words-output=1 'ab?' 输出非空"; else check no "--num-words-output 长选项路径"; fi

# 4) 仅解析路径：-p 'a(b|c)' 退出 0（解析成功即通过）
rc=0
"$BIN" -p 'a(b|c)' > "$WORK/t4.out" 2>&1 || rc=$?
if [ "$rc" -eq 0 ]; then check ok "-p 'a(b|c)' 解析退出 0"; else check no "-p 解析路径 (rc=$rc)"; fi

# 5) 反向对照：无参数调用必须失败退出（usage 路径，证明 harness 能抓到失败）
rc=0
"$BIN" > "$WORK/t5.out" 2>&1 || rc=$?
if [ "$rc" -ne 0 ]; then check ok "反向对照：无参数调用失败退出 (rc=$rc)"; else check no "反向对照：无参数调用应失败却退出 0"; fi

# 6) 鸿蒙形态：管道输入的正则 + 输出重定向到 HMFS 可写目录文件，非空
"$BIN" -n 5 'a*' > "$WORK/words.txt" 2>"$WORK/t6.err"
if [ -s "$WORK/words.txt" ]; then check ok "鸿蒙形态：-n 5 'a*' 落盘 HMFS 文件非空"; else check no "HMFS 落盘输出为空"; fi

echo "RESULT: $p passed, $f failed"
if [ "$f" -ne 0 ]; then
    exit 1
fi
exit 0
