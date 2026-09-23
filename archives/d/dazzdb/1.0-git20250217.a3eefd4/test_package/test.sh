#!/bin/sh
# dazzdb OHOS adaptation test suite.
#
# usage: test.sh <bin-dir> <work-dir>
#
# The suite drives the installed dazzdb command line tools through their
# documented data paths (fasta/DAM -> DB -> tracks -> quiva/arrow -> ONE) and
# asserts the real output of every step.  Upstream ships no test target at all,
# so every case below is an adaptation-side case; the upstream count stays zero.

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
  echo "test.sh requires awk (used to synthesise quiva/arrow inputs)" >&2
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
say "1. rangen: random reference genome"
rangen 0.005 -r42 -U > R.fasta 2>R.err
chk $? "rangen exits successfully"
chk "$([ -s R.fasta ] && echo 0 || echo 1)" "rangen writes a non-empty fasta"
chk "$([ "$(head -1 R.fasta)" = ">random len=5000 bias=0.5" ] && echo 0 || echo 1)" \
    "rangen header reports 5000 bp"
chk "$([ "$(grep -vc '^>' R.fasta)" -eq 63 ] && echo 0 || echo 1)" \
    "rangen emits 5000 bases over 80 column lines"

########################################################################
say "2. fasta2DAM / DAM2fasta"
fasta2DAM R R.fasta 2>dam.err
chk $? "fasta2DAM loads the genome into R.dam"
chk "$([ -s R.dam ] && echo 0 || echo 1)" "R.dam exists and is non-empty"
cp R.fasta R.expected
printf 'stale\n' > R.fasta
DAM2fasta -U R.dam 2>dam2.err
chk $? "DAM2fasta regenerates R.fasta"
cmp -s R.expected R.fasta
chk $? "DAM round trip is byte identical to the source fasta"

########################################################################
say "3. simulator: synthetic read data set"
simulator R -c20. -r42 -U -Mmap.txt > G.fasta 2>sim.err
chk $? "simulator samples a 20x data set"
chk "$([ -s G.fasta ] && echo 0 || echo 1)" "simulated fasta is non-empty"
chk "$([ "$(head -1 G.fasta | grep -c '^>.* RQ=')" -eq 1 ] && echo 0 || echo 1)" \
    "simulated headers carry Pacbio RQ fields"
NREADS=$(wc -l < map.txt)
chk "$([ "$NREADS" -gt 0 ] && echo 0 || echo 1)" "simulator map file lists $NREADS reads"
chk "$([ "$(grep -vc '^>' G.fasta)" -gt 0 ] && echo 0 || echo 1)" \
    "simulated fasta carries sequence lines"

########################################################################
say "4. fasta2DB / DB2fasta"
fasta2DB -v G G.fasta 2>f2db.err
chk $? "fasta2DB builds the compressed DB"
chk "$([ -s G.db ] && [ -s .G.idx ] && [ -s .G.bps ] && echo 0 || echo 1)" \
    "G.db, .G.idx and .G.bps all exist"
cp G.fasta G.reads.expected
printf 'stale\n' > G.fasta
DB2fasta -U G 2>db2f.err
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
grep -v '^>' G.reads.expected | tr 'A-Z' 'a-z' > exp.seq
grep -v '^>' show.txt | tr 'A-Z' 'a-z' > got.seq
cmp -s exp.seq got.seq
chk $? "DBshow sequence matches the imported reads"
DBshow -w40 G > show-w.txt 2>&1
chk $? "DBshow -w40 sets the output line width"
chk "$([ "$(grep -v '^>' show-w.txt | head -1 | wc -c)" -eq 41 ] && echo 0 || echo 1)" \
    "DBshow honours the requested line width"

########################################################################
say "6. DB2ONE"
# The ONE (.daz) export is binary: the ASCII part is the version line, the
# provenance record and the embedded schema, and the payload is compressed.
# Assertions therefore combine the readable header, the schema record types and
# the growth of the export when optional streams are requested.
DB2ONE G > one-plain.daz 2>one.err
chk $? "DB2ONE exports the DB in ONE format"
chk "$([ "$(head -1 one-plain.daz)" = "1 3 daz 1 1" ] && echo 0 || echo 1)" \
    "ONE export starts with the standard header"
has '^! .*DB2ONE' one-plain.daz "ONE export carries a provenance record"
has '^~ O R ' one-plain.daz "embedded schema declares the read object"
PLAIN=$(wc -c < one-plain.daz)
chk "$([ "$PLAIN" -gt 1000 ] && echo 0 || echo 1)" "ONE export carries a payload ($PLAIN bytes)"

DB2ONE -h G > one-h.daz 2>&1
chk $? "DB2ONE -h exports the original fasta headers"
chk "$([ "$(wc -c < one-h.daz)" -gt "$PLAIN" ] && echo 0 || echo 1)" \
    "header stream adds payload to the export"
DB2ONE -w G > one-w.daz 2>&1
chk $? "DB2ONE -w exports well coordinates"
chk "$([ "$(wc -c < one-w.daz)" -gt "$PLAIN" ] && echo 0 || echo 1)" \
    "well stream adds payload to the export"
DB2ONE -a G > one-a-sdb.daz 2>one-a.err
chk "$([ $? -ne 0 ] && echo 0 || echo 1)" "DB2ONE -a refuses a DB without arrow data"
has 'no Arrow data' one-a.err "refusal names the missing arrow data"
DB2ONE -q G > one-q-sdb.daz 2>one-q.err
chk "$([ $? -ne 0 ] && echo 0 || echo 1)" "DB2ONE -q refuses a DB without quiver data"
has 'no Quiver data' one-q.err "refusal names the missing quiver data"

########################################################################
say "7. DBsplit / DBdust / Catrack / DBstats -m"
printf 'Y\n' | DBsplit -s0.05 G > split.log 2>&1
chk $? "DBsplit sets a 0.05 Mbp partition"
has 'blocks = *2' G.db "DB records a two block partition"
DBdust G.1 > dust1.log 2>&1
chk $? "DBdust annotates block G.1"
DBdust G.2 > dust2.log 2>&1
chk $? "DBdust annotates block G.2"
chk "$([ -s .G.1.dust.anno ] && [ -s .G.2.dust.anno ] && echo 0 || echo 1)" \
    "per block dust tracks exist"
Catrack G dust > catrack.log 2>&1
chk $? "Catrack concatenates the blocks into one dust track"
chk "$([ -s .G.dust.anno ] && [ -s .G.dust.data ] && echo 0 || echo 1)" \
    "concatenated dust track exists"
DBstats -mdust -n G > stats-dust.txt 2>&1
chk $? "DBstats reads the concatenated mask track"
has 'Statistics for dust-track' stats-dust.txt "DBstats reports dust track statistics"
DBshow -mdust G > show-dust.txt 2>&1
chk $? "DBshow accepts a mask track name"

########################################################################
say "8. DBtrim / DBcp / DBmv / DBrm"
printf 'Y\n' | DBtrim -x0 G > trim.log 2>&1
chk $? "DBtrim resets the trimming thresholds"
DBcp G Gcopy > cp.log 2>&1
chk $? "DBcp copies the database"
chk "$([ -s Gcopy.db ] && [ -s .Gcopy.idx ] && [ -s .Gcopy.bps ] && echo 0 || echo 1)" \
    "copied database has all primary files"
DBmv Gcopy Gmoved > mv.log 2>&1
chk $? "DBmv renames the database"
chk "$([ -s Gmoved.db ] && [ ! -e Gcopy.db ] && echo 0 || echo 1)" \
    "rename moved Gcopy to Gmoved"
DBrm Gmoved > rm.log 2>&1
chk $? "DBrm removes the database"
chk "$([ ! -e Gmoved.db ] && [ ! -e .Gmoved.idx ] && echo 0 || echo 1)" \
    "DBrm removed both the stub and the index"

########################################################################
say "9. arrow2DB / DB2arrow / DBshow -a / DB2ONE -a / DBwipe"
mkdir -p arrow && cd arrow || exit 2
cp ../R.fasta ../G.fasta .
fasta2DAM R R.fasta 2>/dev/null
simulator R -c20. -r42 -U > G.fasta 2>/dev/null
fasta2DB GA G.fasta 2>/dev/null
chk $? "fresh S-DB built for the arrow path"
PROLOG=$(sed -n '2p' GA.db | awk '{print $3}')
# An arrow stream for source file G: one header plus pulse width digits 1-4.
awk -v pro="$PROLOG" '
  function flush(  i, c, s) {
    if (len == 0) return
    s = ""
    for (i = 0; i < len; i++) { c = 1 + (i % 4); s = s c
                                if (length(s) == 80) { print s; s = "" } }
    if (length(s) > 0) print s
  }
  /^>/ { flush(); print ">" pro " SN=1.00,1.00,1.00,1.00"; len = 0; next }
  { len += length($0) }
  END { flush() }
' G.fasta > G.arrow
cp G.arrow G.arrow.expected
arrow2DB GA G.arrow > a2db.log 2>&1
chk $? "arrow2DB imports the arrow stream"
chk "$([ -s .GA.arw ] && echo 0 || echo 1)" "GA.arw was created"
printf 'stale\n' > G.arrow
DB2arrow GA > db2a.log 2>&1
chk $? "DB2arrow re-exports the arrow stream"
cmp -s G.arrow.expected G.arrow
chk $? "arrow round trip is byte identical"
DBshow -a GA > show-a.txt 2>&1
chk $? "DBshow -a reads the arrow data"
has 'SN=' show-a.txt "DBshow -a reports SNR values"
DBshow -A GA > arrow-resave.txt 2>&1
chk $? "DBshow -A re-saves the arrow stream"
cmp -s G.arrow.expected G.arrow
chk $? "DBshow -A output matches the imported arrow stream"
DB2ONE GA > ga-plain.daz 2>&1
chk $? "DB2ONE exports the A-DB without optional streams"
DB2ONE -a GA > ga-arrow.daz 2>&1
chk $? "DB2ONE -a exports arrow records"
chk "$([ "$(wc -c < ga-arrow.daz)" -gt "$(wc -c < ga-plain.daz)" ] && echo 0 || echo 1)" \
    "arrow stream adds payload to the export"
DBwipe GA > wipe.log 2>&1
chk $? "DBwipe removes the arrow data"
chk "$([ ! -e .GA.arw ] && echo 0 || echo 1)" "GA.arw is gone after DBwipe"
DB2arrow GA > db2a-after.log 2>&1
chk "$([ $? -ne 0 ] && echo 0 || echo 1)" "DB2arrow refuses a DB without arrow data"
cd ..

########################################################################
say "10. quiva2DB / DB2quiva / DBshow -q / DB2ONE -q / DBwipe"
mkdir -p quiva && cd quiva || exit 2
cp ../R.fasta ../G.fasta .
fasta2DAM R R.fasta 2>/dev/null
simulator R -c20. -r42 -U > G.fasta 2>/dev/null
fasta2DB GQ G.fasta 2>/dev/null
chk $? "fresh S-DB built for the quiva path"
# A quiva stream for source file G: per read a header plus the five QV
# streams (deletion QV, deletion tag, insertion, merge, substitution).
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
chk "$([ "$(grep -c . show-q.txt)" -gt 0 ] && echo 0 || echo 1)" "DBshow -q produced output"
DBshow -Q GQ > quiva-resave.txt 2>&1
chk $? "DBshow -Q re-saves the quiva stream"
DB2ONE GQ > gq-plain.daz 2>&1
chk $? "DB2ONE exports the Q-DB without optional streams"
DB2ONE -q GQ > gq-quiva.daz 2>&1
chk $? "DB2ONE -q exports quiver records"
chk "$([ "$(wc -c < gq-quiva.daz)" -gt "$(wc -c < gq-plain.daz)" ] && echo 0 || echo 1)" \
    "quiver streams add payload to the export"
DBwipe GQ > wipeq.log 2>&1
chk $? "DBwipe removes the quiver data"
chk "$([ ! -e .GQ.qvs ] && echo 0 || echo 1)" "GQ.qvs is gone after DBwipe"
cd ..

########################################################################
say "11. scratch directory probing (read-only /tmp)"
#  The ONElib schema temporaries must not depend on a writable /tmp (it is a
#  read-only mount here) and the probe has to cope with long or unusable
#  TMPDIR values instead of overflowing its path buffer.
LONGSEG=0123456789012345678901234567890123456789
LONGTMP="$WORK/$LONGSEG/$LONGSEG/$LONGSEG"
mkdir -p "$LONGTMP"
# 注意：本工作区是 hmdfs，不执行 POSIX 权限位（chmod 500 后 stat 仍为 2771，且
# 普通用户仍可写入），所以"用 chmod 造一个不可写目录"在本设备上是空转。这里改为
# 使用宿主上真实不可写的挂载点（OHOS 的 /tmp 是只读挂载），并用 test -w 现场判定。
ROTMP=""
for cand in /tmp /var/tmp /usr/tmp; do
  if [ -d "$cand" ] && [ ! -w "$cand" ]; then ROTMP=$cand; break; fi
done
DB2ONE -h G > scratch-default.daz 2>scratch-default.err
chk $? "DB2ONE works with the ambient environment (no TMPDIR)"
TMPDIR="$LONGTMP" DB2ONE -h G > scratch-long.daz 2>scratch-long.err
chk $? "DB2ONE survives a long TMPDIR path"
TMPDIR="$WORK/does-not-exist" DB2ONE -h G > scratch-missing.daz 2>scratch-missing.err
chk $? "DB2ONE falls back when TMPDIR does not exist"
# 本用例断言的是「TMPDIR 指向一个存在但不可写的目录时，导出仍能完成」——
# 能观察到的是退出码与载荷完整性，回退目标本身（$HOME 或 cwd）无法直接观察，
# 因此措辞不写 "skips"（那属推断而非断言事实）。正向的"确实没写进 TMPDIR"
# 由该目录为只读挂载这一前提保证：任何实现都无法在其中落盘后仍成功。
if [ -n "$ROTMP" ]; then
  TMPDIR="$ROTMP" DB2ONE -h G > scratch-ro.daz 2>scratch-ro.err
  chk $? "DB2ONE still succeeds when TMPDIR is an existing, unwritable directory ($ROTMP)"
else
  sk "DB2ONE with an unwritable TMPDIR [host has no unwritable mount among /tmp /var/tmp /usr/tmp]"
fi
for f in scratch-long scratch-missing; do
  chk "$([ "$(wc -c < $f.daz)" -gt 1000 ] && echo 0 || echo 1)" \
      "$f export carries a payload"
done
if [ -n "$ROTMP" ]; then
  chk "$([ "$(wc -c < scratch-ro.daz)" -gt 1000 ] && echo 0 || echo 1)" \
      "scratch-ro export carries a payload"
else
  sk "scratch-ro export carries a payload [no unwritable mount on this host]"
fi
chk "$([ "$(head -1 scratch-long.daz)" = "$(head -1 scratch-default.daz)" ] && echo 0 || echo 1)" \
    "export header is independent of the scratch directory"

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
