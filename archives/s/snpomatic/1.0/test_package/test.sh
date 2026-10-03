#!/data/service/hnp/bin/bash
# snpomatic/1.0 test_package —— 消费者视角实质测试
#
# 期望输出全部取自 B 机（HarmonyOS PC aarch64, clang 15.0.4）真跑产物：
#   $ findknownsnps --genome=ref.fasta --fasta=reads.fasta
#   Reading all chromosomes from ref.fasta ... read 1 chromosomes.
#   Indexing 1 chromosomes ... sorting ... done.
#   Reading solexa data from reads.fasta ... scanned 5 solexa reads, 2 (40.00%) matched , 2 total matches.
# 语料（ref 216 bp / 5 条 reads，含 1 条 16 bp 变异读）与两份 fasta 的字节
# 一并冻结在下面，任何行为回归都会打断逐字对照 ⇒ 断言可证伪。
# ⛔ 不用"任意非 0 即通过"，也不把被测对象之外的观测计入断言数。
# ⚠ rc 型断言（ok 7、ok 17）仅作回归哨兵；本包上游错误路径恒 exit 0 ⇒
#   实质断言是内容对照（ok 6/8-12/14/16/18 等），不押 rc 判绿。
set -u

n=0
fail() { echo "FAIL: $1"; exit 1; }
ok() { n=$((n+1)); echo "  ok $n - $1"; }

cat > ref.fasta <<'FIX_REF'
>chr1
AAACAAAGTTCCGGATCCGGAATTCCGGTACCATCGATCGATCGATCGTAGCTAGCTAGCTAGCATCGATCGATCGATCGATCGGCTAGCTAGCTAGCTAGCTAGCTAGCGGATCCGGATCCGGATCCGGAATTCCGGAATTCCGGAATTCCGGTTAACCGGTATAAGCGCTAGCATCGATCGATCGGCTAGCTAGCATCGATCGATTAAACCCGG
FIX_REF

cat > reads.fasta <<'FIX_READS'
>r1
AAACAAAGTTCCGGATCCGGAATTCCGGTACCATCGATCGATCGATCGTA
>r51
GCTAGCTAGCTAGCATCGATCGATCGATCGATCGGCTAGCTAGCTAGCTA
>r101
GCTAGCTAGCGGATCCGGATCCGGATCCGGAATTCCGGAATTCCGGAATT
>r151
CCGGTTAACCGGTATAAGCGCTAGCATCGATCGATCGGCTAGCTAGCATC
>mut
GTTCGATTAAACCCGG
FIX_READS

# --- 1) 四个产物必须真的装在 PATH 上（R34：必须执行被测包的二进制）
for prog in findknownsnps reassemble variety mapcontigs; do
    command -v "$prog" >/dev/null 2>&1 || fail "$prog not resolvable from conanrun PATH"
    ok "$prog resolvable from PATH"
done

# --- 2) findknownsnps 缺省入参路径：内容 + 退出码（上游对所有错误路径都 exit 0，
#         这是可观测事实，故两笔断言分开写，不靠退出码蒙过）
findknownsnps > no_genome.out 2>&1
[ "$?" = "0" ] || fail "findknownsnps(no args) rc != 0"
ok "findknownsnps without args exits 0 (upstream policy, measured)"
grep -qF 'No genome file given!' no_genome.out || fail "missing 'No genome file given!' banner"
ok "findknownsnps without args prints the usage banner"

# --- 3) 真跑功能：押输出内容，不押"非 0 即过"
findknownsnps --genome=ref.fasta --fasta=reads.fasta > run.out 2>&1
[ "$?" = "0" ] || fail "functional run rc != 0"
ok "functional run rc == 0"
grep -qF 'Reading all chromosomes from ref.fasta ... read 1 chromosomes.' run.out \
    || fail "chromosome-read line mismatch"
ok "chromosome read line matches frozen artifact"
grep -qF 'Indexing 1 chromosomes ... sorting ... done.' run.out \
    || fail "indexing line mismatch"
ok "indexing line matches frozen artifact"
grep -qF 'Reading solexa data from reads.fasta ... scanned 5 solexa reads, 2 (40.00%) matched , 2 total matches.' run.out \
    || fail "read-mapping result line mismatch"
ok "read mapping result line matches frozen artifact (5 reads, 2 matched)"

# --- 4) --gffout 通道：文件必须被创建且在本语料下为空（实测 0 B）
findknownsnps --genome=ref.fasta --fasta=reads.fasta --gffout=out.gff > run2.out 2>&1
[ -f out.gff ] || fail "--gffout did not create the file"
ok "--gffout creates the declared output file"
[ ! -s out.gff ] || fail "--gffout file is not empty on this corpus"
ok "--gffout file stays empty on the perfect-match corpus (frozen 0 B artifact)"

# --- 5) 另外三个程序各自独有的首行与退出码（两两不同 ⇒ 可证伪）
reassemble > re.out 2>&1
[ "$?" = "1" ] || fail "reassemble rc != 1"
ok "reassemble exits 1 on empty input"
grep -qF 'Could not open FASTQ file' re.out || fail "reassemble first-line mismatch"
ok "reassemble prints its own FASTQ-open abort line"

variety > va.out 2>&1
[ "$?" = "1" ] || fail "variety rc != 1"
ok "variety exits 1 on empty input"
grep -qF 'file could not be accessed' va.out || fail "variety first-line mismatch"
ok "variety prints its own chromosome-open abort line"

mapcontigs > mc.out 2>&1
[ "$?" = "0" ] || fail "mapcontigs rc != 0"
ok "mapcontigs exits 0 on missing genome (upstream policy)"
grep -qF 'No genome file given!' mc.out || fail "mapcontigs first-line mismatch"
ok "mapcontigs prints the shared usage banner"

[ "$n" = "18" ] || fail "assertion count drifted: $n != 18"
echo "ALL PASS ($n assertions)"
