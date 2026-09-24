#!/bin/sh
# lnav test_package —— 真跑包内 lnav 二进制的消费者测试（鸿蒙特有，6 项断言）
# 被测物：conan runenv PATH 里的 <package>/bin/lnav（self.run(env="conanrun")）
# 断言面：版本自报 / syslog 格式识别+SQL 计数（pcre2+sqlite3）/ gzip、bzip2
# 透明解压（zlib、bzip2）/ 纯文本格式探测负路径（lnav_file）/ SQL 标量表达式
# （sqlite3）。
set -u
fail=0
WORK="${TMPDIR:-$(pwd)}"
mkdir -p "$WORK"
FIX_SRC="$(dirname "$0")/fixtures"
cp "$FIX_SRC/syslog.f" "$WORK/syslog.f"
# 压缩夹具用 python3 标准库生成（不依赖外部 gzip/bzip2 CLI 是否在 PATH）
python3 - "$WORK" <<'PYEOF'
import bz2, gzip, sys, pathlib
w = pathlib.Path(sys.argv[1])
data = (w / "syslog.f").read_bytes()
(w / "syslog.f.gz").write_bytes(gzip.compress(data))
(w / "syslog.f.bz2").write_bytes(bz2.compress(data))
PYEOF
printf 'plain line one\nplain line two\n' > "$WORK/plain.txt"

run_sql() {
    # run_sql <file> <sql>  → 输出取最后一行（lnav -n 的表格输出末行为数据行）
    lnav -n -c ";$2" "$1" 2>"$WORK/lnav.err" | tail -1
}

# A1: --version 自报版本与包版本一致（tarball 无 .git，VCS_PACKAGE_STRING 回退
#     PACKAGE_STRING = "lnav 0.13.2"）
v=$(lnav -V 2>&1 | tail -1)
if [ "$v" = "lnav 0.13.2" ]; then
    echo "A1 PASS: lnav -V => $v"
else
    echo "A1 FAIL: lnav -V => '$v'"; fail=1
fi

# A2: syslog 格式识别 + all_logs SQL 计数（pcre2 格式探测 + sqlite3 引擎）
n=$(run_sql "$WORK/syslog.f" "SELECT count(*) AS n FROM all_logs" | grep -o '[0-9]*' | tail -1)
if [ "$n" = "3" ]; then
    echo "A2 PASS: syslog 解析 all_logs count => $n"
else
    echo "A2 FAIL: all_logs count => '$n'"; fail=1
fi

# A3: gzip 透明解压后同一计数（zlib 路径）
n=$(run_sql "$WORK/syslog.f.gz" "SELECT count(*) AS n FROM all_logs" | grep -o '[0-9]*' | tail -1)
if [ "$n" = "3" ]; then
    echo "A3 PASS: gzip 透明解压 all_logs count => $n"
else
    echo "A3 FAIL: gzip all_logs count => '$n'"; fail=1
fi

# A4: bzip2 透明解压后同一计数（bzip2 路径）
n=$(run_sql "$WORK/syslog.f.bz2" "SELECT count(*) AS n FROM all_logs" | grep -o '[0-9]*' | tail -1)
if [ "$n" = "3" ]; then
    echo "A4 PASS: bzip2 透明解压 all_logs count => $n"
else
    echo "A4 FAIL: bzip2 all_logs count => '$n'"; fail=1
fi

# A5: 纯文本文件的格式探测负路径：文件被完整加载（lines=2）但不匹配任何日志
#     格式（format IS NULL），all_logs 不产生消息——这是 lnav 0.13.2 的设计
#     行为（实测 lnav_file.format=<NULL>；上游 test_cli.sh:35 同用 lnav_file
#     口径）。断言取「加载成功 + 格式未识别」这一负路径结果。
n=$(run_sql "$WORK/plain.txt" "SELECT count(*) AS n FROM lnav_file WHERE lines = 2 AND format IS NULL" | grep -o '[0-9]*' | tail -1)
if [ "$n" = "1" ]; then
    echo "A5 PASS: 纯文本格式探测负路径 lnav_file => $n"
else
    echo "A5 FAIL: 纯文本格式探测负路径 lnav_file => '$n'"; fail=1
fi

# A6: SQL 标量表达式（sqlite3 活性）
n=$(run_sql "$WORK/syslog.f" "SELECT 40 + 2 AS n" | grep -o '[0-9]*' | tail -1)
if [ "$n" = "42" ]; then
    echo "A6 PASS: SQL 标量表达式 => $n"
else
    echo "A6 FAIL: SQL 标量表达式 => '$n'"; fail=1
fi

if [ "$fail" = "0" ]; then
    echo "test_package: 6/6 assertions passed"
    exit 0
fi
echo "test_package: FAILURES present"
exit 1
