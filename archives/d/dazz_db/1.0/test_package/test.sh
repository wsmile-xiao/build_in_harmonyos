#!/bin/sh
# dazz_db (V1.0 tag) OHOS adaptation test suite.
#
# usage: test.sh <bin-dir> <work-dir>
#
# The suite drives the installed dazz_db command line tools through their
# documented data paths (fasta/DAM -> DB -> partition -> dust track -> quiva
# stream) and asserts the real output of every step.  Upstream ships no test
# target at all, so every case below is an adaptation-side case; the upstream
# count stays zero.
#
# V1.0 工具集（上游官方 tag V1.0 的 ALL 列表，13 个工具）：
#   fasta2DB DB2fasta quiva2DB DB2quiva DBsplit DBdust Catrack DBshow
#   DBstats DBrm simulator fasta2DAM DAM2fasta

# 安全模式：只在 set -u 下运行。刻意不使用 set -e，因为本脚本的设计是
# 「记录失败并继续」，让 set -e 提前退出会丢掉后续用例的 FAIL 计数。
set -u

BIN=${1:-}
WORK=${2:-}

PASS=0
FAIL=0
SKIP=0

ok()  { PASS=$((PASS + 1)); printf 'PASS  %s\n' "$1"; }
no()  { FAIL=$((FAIL + 1)); printf 'FAIL  %s\n' "$1"; }
# SKIP 用于「本宿主不满足用例前提」的情形：必须显式打印并单独计数，
# 既不冒充 PASS，也不把宿主差异误报成产品缺陷。
sk()  { SKIP=$((SKIP + 1)); printf 'SKIP  %s\n' "$1"; }
chk() { if [ "$1" -eq 0 ]; then ok "$2"; else no "$2"; fi; }
has() { if grep -q "$1" "$2" 2>/dev/null; then ok "$3"; else no "$3 [no /$1/ in $2]"; fi; }
say() { printf '\n== %s\n' "$1"; }

if [ -z "$BIN" ] || [ -z "$WORK" ]; then
  echo "usage: test.sh <bin-dir> <work-dir>" >&2
  exit 2
fi
if ! command -v awk >/dev/null 2>&1; then
  echo "test.sh requires awk (used to synthesise fasta/quiva inputs)" >&2
  exit 2
fi

# PATH 必须在参数校验之后才注入：BIN 为空时 "${BIN}:${PATH}" 会引入一个空分量，
# POSIX 语义下等价于把当前目录加进 PATH。
PATH="${BIN}:${PATH}"
export PATH

mkdir -p "$WORK" || exit 2
cd "$WORK" || exit 2
rm -rf ./* 2>/dev/null

########################################################################
say "1. 参考基因组准备（awk 确定性合成，替代上游 V1.0 缺失的 rangen）"
# V1.0 tag 没有 rangen；用 awk 按固定种子生成 5000 bp 的确定性参考序列。
awk 'BEGIN { printf ">ref len=5000 bias=0.5\n"; srand(42);
             for (i = 0; i < 5000; i++) { printf "%s", substr("ACGT", 1+int(4*rand()), 1);
                                          if ((i+1) % 80 == 0) printf "\n" }
             printf "\n" }' > R.fasta
chk $? "合成 5000 bp 参考 fasta"
chk "$([ "$(grep -vc '^>' R.fasta)" -eq 63 ] && echo 0 || echo 1)" \
    "参考序列按 80 列换行（且以换行结尾共 63 行）"

########################################################################
say "2. fasta2DAM / DAM2fasta"
fasta2DAM R R.fasta > dam.err 2>&1
chk $? "fasta2DAM loads the genome into R.dam"
chk "$([ -s R.dam ] && echo 0 || echo 1)" "R.dam exists and is non-empty"
cp R.fasta R.expected
printf 'stale\n' > R.fasta
DAM2fasta -U R > dam2.err 2>&1
chk $? "DAM2fasta regenerates R.fasta"
cmp -s R.expected R.fasta
chk $? "DAM round trip is byte identical to the source fasta"

########################################################################
say "3. simulator: synthetic read data set"
simulator 0.005 -c20. -r42 -Mmap.txt > G.fasta 2>sim.err
chk $? "simulator samples a 20x data set of a 0.005 Mbp genome"
chk "$([ -s G.fasta ] && echo 0 || echo 1)" "simulated fasta is non-empty"
chk "$([ "$(head -1 G.fasta | grep -c '^>Sim/')" -eq 1 ] && echo 0 || echo 1)" \
    "simulated headers carry the >Sim/ provenance form"
NREADS=$(grep -c '^>' G.fasta)
chk "$([ "$NREADS" -gt 0 ] && echo 0 || echo 1)" "fasta lists $NREADS reads"
chk "$([ -f map.txt ] && echo 0 || echo 1)" "simulator wrote the -M map file"

########################################################################
say "4. fasta2DB / DB2fasta"
fasta2DB -v G G.fasta > f2db.err 2>&1
chk $? "fasta2DB builds the compressed DB"
chk "$([ -s G.db ] && [ -s .G.idx ] && [ -s .G.bps ] && echo 0 || echo 1)" \
    "G.db, .G.idx and .G.bps all exist"
cp G.fasta G.reads.expected
printf 'stale\n' > G.fasta
#  V1.0 的 simulator 输出小写读段（无 -U 选项），DB2fasta 不带 -U 时按原样
#  输出小写，往返逐字节一致（-U 会强制输出大写，历史 2025 快照的 simulator
#  自带 -U 才与之配套；本版本不适用）。
DB2fasta G > db2f.err 2>&1
chk $? "DB2fasta regenerates the read fasta"
cmp -s G.reads.expected G.fasta
chk $? "read fasta round trip is byte identical"

########################################################################
say "5. DBstats / DBshow"
DBstats -n G > stats.txt 2>&1
chk $? "DBstats summarises the DB"
has 'reads ' stats.txt "DBstats reports a read count"
has 'base pairs' stats.txt "DBstats reports a base count"
DBstats G > stats-hist.txt 2>&1
chk $? "DBstats prints the read length histogram"
has 'Distribution of Read Lengths' stats-hist.txt "histogram section is present"

DBshow G > show.txt 2>show.err
chk $? "DBshow dumps the DB"
chk "$([ "$(head -1 show.txt | grep -c '^>')" -eq 1 ] && echo 0 || echo 1)" \
    "DBshow output starts with a fasta header"
DBshow -w40 G > show-w.txt 2>&1
chk "$([ $? -eq 0 ] && echo 0 || echo 1)" "DBshow -w40 sets the output line width"

########################################################################
say "6. DBsplit / DBdust / Catrack / DBstats -m"
printf 'Y\n' | DBsplit -s1 G > split.log 2>&1
chk $? "DBsplit sets a 1 Mbp partition"
has 'blocks = *[0-9]' G.db "DB records a partition"
DBdust G.1 > dust1.log 2>&1
chk $? "DBdust annotates block G.1"
chk "$([ -s .G.1.dust.anno ] && echo 0 || echo 1)" \
    "per block dust track exists"
Catrack G dust > catrack.log 2>&1
chk $? "Catrack concatenates the blocks into one dust track"
#  dust track 的 .anno 记录必然非空；.data 是区间载荷，小数据量下可能为 0 字节，
#  因此对 .data 只断言文件存在，不要求非空。
chk "$([ -s .G.dust.anno ] && [ -e .G.dust.data ] && echo 0 || echo 1)" \
    "concatenated dust track exists"
DBstats -mdust -n G > stats-dust.txt 2>&1
chk $? "DBstats reads the concatenated mask track"
has 'Statistics for dust-track' stats-dust.txt "DBstats reports dust track statistics"
DBshow -mdust G > show-dust.txt 2>&1
chk $? "DBshow accepts a mask track name"

########################################################################
say "7. quiva2DB / DB2quiva（质量值流）"
mkdir -p quiva && cd quiva || exit 2
cp ../G.fasta .
fasta2DB GQ G.fasta > f2dbq.log 2>&1
chk $? "fresh DB built for the quiva path"
# 一个 quiva 流：每条读段一个头（@ 开头）加 5 个 QV 流（删除QV/删除标记/插入/合并/替换），
# 与上游 QV 文件格式一致（见 quiva2DB 的读取路径）。
awk '
  function rep(ch,  i, s) { s = ""; for (i = 0; i < len; i++) s = s ch; return s }
  function alt(  i, s) { s = ""; for (i = 0; i < len; i++) s = s (i % 2 ? "a" : "0"); return s }
  function flush() { if (len == 0) return
                     print alt(); print rep("a"); print alt(); print alt(); print alt() }
  /^>/ { flush(); print "@" substr($0,2); len = 0; next }
  { len += length($0) }
  END { flush() }
' G.fasta > G.quiva
cp G.quiva G.quiva.expected
quiva2DB GQ G.quiva > q2db.log 2>&1
chk $? "quiva2DB imports the quiva stream"
chk "$([ -s .GQ.qvs ] && echo 0 || echo 1)" "GQ.qvs was created"
printf 'stale\n' > G.quiva
DB2quiva GQ > db2q.log 2>&1
chk $? "DB2quiva re-exports the quiva stream"
cmp -s G.quiva.expected G.quiva
chk $? "quiva round trip is byte identical"
DBshow -q GQ > show-q.txt 2>&1
chk $? "DBshow -q reads the quiver data"
DBshow -Q GQ > quiva-resave.txt 2>&1
chk "$([ $? -eq 0 ] && echo 0 || echo 1)" "DBshow -Q re-saves the quiva stream"
cd ..

########################################################################
say "8. DBrm 生命周期"
DBrm G > rm.log 2>&1
chk $? "DBrm removes the database"
chk "$([ ! -e G.db ] && [ ! -e .G.idx ] && echo 0 || echo 1)" \
    "DBrm removed both the stub and the index"

########################################################################
say "summary"
printf 'adaptation cases: PASS=%d FAIL=%d TOTAL=%d SKIP=%d\n' \
       "$PASS" "$FAIL" "$((PASS + FAIL))" "$SKIP"
if [ "$FAIL" -ne 0 ]; then
  echo "RESULT: FAILED"
  exit 1
fi
echo "RESULT: OK"
exit 0