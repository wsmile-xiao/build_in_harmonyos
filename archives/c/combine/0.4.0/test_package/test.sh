#!/bin/sh
# combine 0.4.0 消费者行为测试源文件（test_package/test.sh，由 conanfile.py 的 test()
# 以 conanrun 环境调用；与 conanfile.py 上方声明同源）
#
# 口径：以 combine 的**使用者**身份运行打包出来的二进制，每项断言同时看
# **退出码**和**输出**（手册04 §9 / R34：只打印、只查文件、只链接均不合格）。
# combine 是纯 CLI（无库产物），所以消费者测试走命令行行为而非 API 链接。
#
# 计数口径：按下面的「7 个编号节」计 7 项断言（第 7 节内含 7a/7b 两项反向检查，
# 所以检查项是 8）；同一口径同步在 test_package/conanfile.py docstring、
# test_package/MANIFEST.yml、notes.md 与版本级 manifest.yaml 五处，⛔ 只改一处。
# 期望值不是从日志反填的：字段投影 / 引用匹配数都由本脚本自己写下的输入数据
# 按 combine --help  documented 语义推出来（见每条断言旁边的推导）。
set -e

CB=combine
fail() {
    echo "FAIL: $*" >&2
    exit 1
}

# 所有中间产物只写进一个一次性工作目录，退出即清 —— ⛔ 把数据件/输出件落在
# test_package/ 里（conan 默认把 generators 写在 recipe_folder，也就是归档目录，
# 再往里撒测试数据就会污染配方树）。$TMPDIR 在目标上是可写的（/tmp 只读，E002）。
BASE="${TMPDIR:-$HOME}"
W="$BASE/combine-consumer-test.$$"
if ! mkdir -p "$W" 2>/dev/null; then
    W="./combine-consumer-test.$$"
    mkdir -p "$W" || fail "cannot create a writable work dir"
fi
cd "$W" || fail "cannot enter work dir $W"
cleanup() { cd "$OLDPWD" 2>/dev/null || true; rm -rf "$W" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

# 测试数据（与断言里的期望值一一对应）
printf 'a,b,c\nd,e,f\ng,h,i\n' > in.csv     # 3 条记录，逗号分隔
printf '1 apple\n2 banana\n3 cherry\n' > d1  # 数据文件：键 1/2/3
printf '1 one\n3 three\n' > r1               # 引用文件：键 1/3
printf '1 x\n1 y\n2 z\n' > d2                # 重复键 1,1,2

# ---- 1) --version：退出码 0 + stdout 必须是本包版本
out=$($CB --version 2>&1) || fail "combine --version exited non-zero"
case "$out" in
    *"combine (combine) 0.4.0"*) : ;;
    *) fail "--version did not report 0.4.0, got: $out" ;;
esac

# ---- 2) --help：退出码 0 + stdout 含用法首行（证明 CLI 解析层真的编进去了）
out=$($CB --help 2>&1) || fail "combine --help exited non-zero"
case "$out" in
    *"combine -- flexible file joins"*) : ;;
    *) fail "--help missing usage banner" ;;
esac

# ---- 3) 字段投影（核心功能）：-D , 按逗号切字段，-o 1,3 取第 1、3 字段
#        输入 a,b,c / d,e,f / g,h,i  ⇒ 期望逐字节 a,c / d,f / g,i
$CB -D , -o 1,3 -w in.csv > p.out 2>/dev/null || fail "field projection exited non-zero"
printf 'a,c\nd,f\ng,i\n' > p.want
if ! diff -q p.out p.want >/dev/null 2>&1; then
    echo "--- got  ---"; cat p.out
    echo "--- want ---"; cat p.want
    fail "field projection (-D , -o 1,3) output mismatch"
fi

# ---- 4) -t 指定输出文件：投影第 2 字段应写成 b / e / h
$CB -D , -o 2 -w -t t.out in.csv >/dev/null 2>&1 || fail "-t output exited non-zero"
printf 'b\ne\nh\n' > t.want
if ! diff -q t.out t.want >/dev/null 2>&1; then
    echo "--- got  ---"; cat t.out
    fail "-t file content mismatch"
fi

# ---- 5) 引用文件匹配（combine 的看家功能）：d1 的键 {1,2,3} 对 r1 的键 {1,3}
#        ⇒ 命中 2 条。combine 把统计写到 stderr（实测默认就写，不需要 --statistics），
#        这里断言 stderr 里的两个匹配计数。
$CB -o 2 -w -r r1 -k 1 -m 1 d1 > j.out 2> j.err || fail "reference join exited non-zero"
case "$(cat j.err)" in
    *"Number of reference-data matches:"*) : ;;
    *) fail "join did not emit statistics on stderr" ;;
esac
if ! grep -q "Number of records read:                            3" j.err; then
    fail "data file record count != 3 (see j.err)"
fi
if ! grep -q "Number of reference-data matches:                  2" j.err; then
    echo "--- j.err ---"; cat j.err
    fail "expected exactly 2 reference-data matches (keys 1 and 3)"
fi

# ---- 6) 未加 -u 时不合并重复键：d2 的记录键是 1,1,2，经 -o 1 -w 投影第 1 字段
#        ⇒ 三行 1 / 1 / 2（重复的那条没有被吞掉）
$CB -n -o 1 -w d2 > u.out 2>/dev/null || fail "count pass exited non-zero"
printf '1\n1\n2\n' > u.want
if ! diff -q u.out u.want >/dev/null 2>&1; then
    echo "--- got ---"; cat u.out
    fail "duplicate key handling mismatch"
fi

# ---- 7) 反向断言（证明错误路径没有被吞掉）
#   7a) 数据文件不存在 ⇒ 非零退出
if $CB -o 1 -w no-such-file.dat >/dev/null 2>&1; then
    fail "missing data file should exit non-zero"
fi
#   7b) -u（唯一化）是"引用文件选项"，写在任何 -r 之前属于用法错误
#       ⇒ combine 自己报错并非零退出（实测 stderr: "option u listed before
#          any reference file was specified"）
if $CB -u -o 1 -w d1 >/dev/null 2>&1; then
    fail "-u before any reference file should exit non-zero"
fi

echo "consumer test passed: 7/7 assertions (7 numbered sections: 1-6 positive command behaviours + section 7 holding 2 negative checks 7a/7b)"
