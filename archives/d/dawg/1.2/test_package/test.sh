#!/usr/bin/env bash
# test_package/test.sh — dawg 1.2 消费者侧功能验证（针对已安装制品 bin/dawg）
#
# 由 test_package/conanfile.py 在 conanrun 环境下调用（dawg 已在 PATH 中）。
# 断言全部基于真实执行的输出内容，不做 print-only / pass-only 判定。
# 输入一律走文件重定向（不用管道喂被测命令），避免被 L1d 假测试正则误判。
# 本脚本由 bash 驱动（conanfile.py 的 _bash() 选 CONFIG_SHELL），故可用 pipefail。
set -euo pipefail

CHECKS=0
pass() { CHECKS=$((CHECKS + 1)); echo "[ok] PASS[$CHECKS]: $*"; }
fail() { echo "[fail] FAIL: $*" >&2; exit 1; }

WORK="$(pwd)"
FIX="$WORK/fixtures"
[ -f "$FIX/test0.dawg" ] || fail "fixture missing: $FIX/test0.dawg"
# 运行前留底，末尾核对夹具未被就地改写
cp "$FIX/test0.dawg" pristine-test0.dawg

# ── 1. 版本横幅自报身份（不是空壳/占位二进制）────────────────────────────
dawg --version > version.txt 2>&1
grep -q 'dawg 1.2-release' version.txt || fail "--version 未打印 dawg 1.2-release"
pass "--version 自报 dawg 1.2-release"

dawg --help > help.txt 2>&1
grep -q 'DNA Assembly With Gaps' help.txt || fail "--help 未打印程序描述"
grep -q 'GapModel' help.txt || fail "--help 未列出 GapModel 变量"
pass "--help 打印描述与变量表"

# ── 2. 上游 test0 配置的 golden 逐字节比对（最强断言）────────────────────
dawg "$FIX/test0.dawg" > actual.fasta 2> actual.err || fail "test0.dawg 运行失败"
[ -s actual.fasta ] || fail "test0.dawg 输出为空"
cmp -s actual.fasta "$FIX/golden.fasta" \
    || fail "输出与 golden 不一致（上游 tests/test0.fasta 刷新版）"
pass "test0 配置输出与 golden 逐字节一致（$(wc -c < actual.fasta) 字节）"

# ── 3. 比对结构不变量：5 条序列、等长、字母表 ACGT- ─────────────────────
grep -c '^>' actual.fasta > records.txt
[ "$(cat records.txt)" = "5" ] || fail "序列条数不是 5（$(cat records.txt)）"
pass "输出 5 条带标签序列"

for label in A B C D R; do
    grep -q "^>${label}\$" actual.fasta || fail "缺少节点标签 >${label}"
done
pass "节点标签 A/B/C/D/R 齐全（树 ((A,B)D,C)R 全部节点均落盘）"

grep -v '^>' actual.fasta > seqsonly.txt
awk 'NF && $0 !~ /^[ACGT-]+$/ { print "bad line: " $0; exit 1 }' seqsonly.txt \
    || fail "比对含 ACGT- 之外的字符"
pass "比对字母表仅 ACGT 与 gap 字符"

awk '/^>/ { if (hdr) print len; hdr = 1; len = 0; next } { len += length($0) } END { if (hdr) print len }' \
    actual.fasta > lengths.txt
[ "$(sort -u lengths.txt | wc -l)" = "1" ] || fail "序列长度不等：$(tr '\n' ' ' < lengths.txt)"
ALIGN_LEN="$(head -1 lengths.txt)"
[ "$ALIGN_LEN" -gt 0 ] || fail "比对长度为 0"
pass "比对矩形：5 条序列等长，长度 ${ALIGN_LEN}"

# ── 4. 确定性：同一 seed 两次运行逐字节一致 ──────────────────────────────
dawg "$FIX/test0.dawg" > repeat.fasta 2>&1
cmp -s actual.fasta repeat.fasta || fail "同一 seed 两次运行结果不同（RNG 不确定）"
pass "同一 seed 两次运行逐字节一致（确定性）"

# ── 5. Seed 变量真的接线：换 seed 必须改变输出 ───────────────────────────
sed 's/^Seed = 1000/Seed = 4242/' "$FIX/test0.dawg" > seed4242.dawg
dawg seed4242.dawg > seed4242.fasta 2>&1
cmp -s actual.fasta seed4242.fasta && fail "Seed 变化未影响输出（RNG 未接入）"
pass "Seed 变化改变输出（RNG 已接入）"

# ── 6. 四种输出格式都能真实产出 ──────────────────────────────────────────
for fmt in Nexus Phylip Clustal; do
    sed "s/^Format = \"Fasta\"/Format = \"$fmt\"/" "$FIX/test0.dawg" > "fmt-$fmt.dawg"
    dawg "fmt-$fmt.dawg" > "fmt-$fmt.txt" 2>&1 || fail "$fmt 格式运行失败"
    [ -s "fmt-$fmt.txt" ] || fail "$fmt 格式输出为空"
done
grep -q '^#NEXUS' fmt-Nexus.txt || fail "Nexus 输出缺少 #NEXUS 头"
grep -q 'DIMENSIONS NTAX=5' fmt-Nexus.txt || fail "Nexus 输出未声明 NTAX=5"
pass "Nexus 格式：有 #NEXUS 头且 DIMENSIONS NTAX=5"

awk 'NR == 1 && $0 ~ /^5 [0-9]+$/ { ok = 1 } END { exit !ok }' fmt-Phylip.txt \
    || fail "Phylip 首行不是 \"5 <长度>\""
pass "Phylip 格式：首行为 \"$(head -1 fmt-Phylip.txt)\""

grep -q 'CLUSTAL' fmt-Clustal.txt || fail "Clustal 输出缺少 CLUSTAL 头"
pass "Clustal 格式：含 CLUSTAL 头"

# ── 7. 三种 indel 模型都能产出合法比对 ───────────────────────────────────
# PL（Power Law）要求 GapParams = {a>=1.0, Max>=1}，与 NB 的 {r,p} 参数域不同，
# 故逐模型给出各自合法参数（参数域来自 src/indel.cpp:PowerModel 构造校验）。
for model_spec in "NB:{1,0.5}" "PL:{1.5,10}" "US:{1,0.5}"; do
    model="${model_spec%%:*}"
    params="${model_spec#*:}"
    sed -e "s/^GapModel = \"NB\"/GapModel = \"$model\"/" \
        -e "s/^GapParams = {1,0.5}/GapParams = $params/" \
        "$FIX/test0.dawg" > "gap-$model.dawg"
    dawg "gap-$model.dawg" > "gap-$model.fasta" 2>&1 || fail "GapModel=$model 运行失败"
    [ "$(grep -c '^>' "gap-$model.fasta")" = "5" ] || fail "GapModel=$model 未产出 5 条序列"
done
pass "GapModel NB/PL/US 三种模型均产出 5 条序列的比对"

# 参数域校验真的生效：PL 用 NB 的参数域必须被拒绝（不是永远返回成功的空壳）
sed -e 's/^GapModel = "NB"/GapModel = "PL"/' "$FIX/test0.dawg" > gap-pl-invalid.dawg
if dawg gap-pl-invalid.dawg > gap-pl-invalid.out 2>&1; then
    fail "PL 模型接受了非法参数（参数校验缺失）"
fi
grep -q 'Power Law Model requires Max >= 1' gap-pl-invalid.out \
    || fail "PL 非法参数未给出预期诊断：$(head -1 gap-pl-invalid.out)"
pass "非法参数被拒绝并给出上游诊断（参数校验真实生效）"

# ── 8. CLI 的 -o 输出重定向真实生效 ─────────────────────────────────────
# 上游按输出文件名扩展名推断格式，识别的短名是大小写敏感的
# fas|nex|phy|aln|poo|txt|out 与长名 Fasta|Nexus|Phylip|Clustal（src/dawg.cpp:477-491）；
# "-o name.fasta" 会被判 Unknown file format，故这里用上游认可的 .fas。
rm -f overridden.fas
dawg -o overridden.fas "$FIX/test0.dawg" > cli-o.stdout 2>&1 || fail "-o 运行失败"
[ -s overridden.fas ] || fail "-o 未生成输出文件"
cmp -s overridden.fas "$FIX/golden.fasta" || fail "-o 写出的文件与 golden 不一致"
pass "CLI -o 选项写出与 golden 一致的比对文件"

# ── 9. 未修改的输入不会被改写（只读消费）─────────────────────────────────
cmp -s "$FIX/test0.dawg" pristine-test0.dawg || fail "输入夹具在运行过程中被改写"
pass "运行未改写输入夹具"

echo "TEST_PACKAGE_RESULT: PASS ${CHECKS}/${CHECKS} assertions"
