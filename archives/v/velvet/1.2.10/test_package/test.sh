#!/data/service/hnp/bin/bash
# test_package/test.sh — velvet 1.2.10 功能验证（运行于 conanrun 环境）
#
# 覆盖:
#   U1-U5  上游官方测试套件 tests/run-tests.sh 的 5 个 .t 用例
#          （fasta_eq_fastq_ascii / fasta_eq_fastq_binary / fmt_auto_mode /
#          interleaved_eq_separate / mismatched_separates），脚本与数据
#          原样来自上游 tests/，未修改。
#   H1     鸿蒙特有 e2e：velveth → velvetg 完整组装流程（rule12）。
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/velvet-test.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

fail() { echo "FAIL: $1" >&2; exit 1; }
ok()   { echo "PASS: $1"; }

command -v velveth >/dev/null || fail "velveth 不在 PATH（conanrun 环境缺失）"
command -v velvetg >/dev/null || fail "velvetg 不在 PATH（conanrun 环境缺失）"
VH_BIN="$(command -v velveth)"
VG_BIN="$(command -v velvetg)"

# ─────────────────────────────────────────────────────────────────────────────
# U1-U5: 上游官方测试套件（原样重放）
#   上游 tests/*.t 通过 ../velveth、../velvetg 相对路径调用二进制。
#   在 $WORK 下按相同布局放置 shell 包装脚本，exec 已安装的真实产物；
#   不复制/重命名 ELF（OHOS codesign 约束），上游测试脚本零修改。
# ─────────────────────────────────────────────────────────────────────────────
mkdir -p "$WORK/suite"
cp -R "$SCRIPT_DIR/corpus/tests/." "$WORK/suite/"

# corpus 内 6 个 .gz 输入以未压缩明文存储（GitCode PR diff 不携带二进制
# 补丁数据，CI 的 git apply 无法应用二进制文件，PR #14063 首轮 CI 即因此
# 失败）；此处现场压缩回 .gz。gzip 只影响容器字节，解压内容与上游原 .gz
# 完全一致，所有 cmp 断言比较的是解压产物（Sequences/Roadmaps），不受影响。
cd "$WORK/suite"
for f in read1.fa read1.fq read2.fa read2.fq reads.fa reads.fq; do
  gzip -c "$f" > "$f.gz" || fail "生成 $f.gz 失败（gzip 不可用？）"
done
cd "$WORK"
printf '#!/bin/sh\nexec "%s" "$@"\n' "$VH_BIN" > "$WORK/velveth"
printf '#!/bin/sh\nexec "%s" "$@"\n' "$VG_BIN" > "$WORK/velvetg"
chmod +x "$WORK/velveth" "$WORK/velvetg"

cd "$WORK/suite"
bash ./run-tests.sh || fail "上游测试套件 run-tests.sh 未全部通过"
ok "U1-U5 上游官方测试套件 5/5 通过（runner 口径 NUMTESTS=5）"

# ─────────────────────────────────────────────────────────────────────────────
# H1: 鸿蒙特有 e2e —— 安装产物完整组装流程（velveth → velvetg）
#     在 HarmonyOS 上真实执行 k=21 短读组装，验证：
#       a) velveth 生成非空 Sequences / Roadmaps
#       b) velvetg 生成非空 contigs.fa 且含 FASTA 头
# ─────────────────────────────────────────────────────────────────────────────
cd "$WORK"
velveth asm 21 -fasta.gz -short "$WORK/suite/reads.fa.gz" > velveth.log 2>&1 \
  || fail "H1 velveth 执行失败（详见 velveth.log）"
[ -s asm/Sequences ] || fail "H1 velveth 未生成非空 Sequences"
[ -s asm/Roadmaps ]  || fail "H1 velveth 未生成非空 Roadmaps"

velvetg asm > velvetg.log 2>&1 \
  || fail "H1 velvetg 执行失败（详见 velvetg.log）"
[ -s asm/contigs.fa ] || fail "H1 velvetg 未生成非空 contigs.fa"
grep -q '^>' asm/contigs.fa || fail "H1 contigs.fa 不含 FASTA 头"
ok "H1 鸿蒙特有 e2e：velveth→velvetg 完整组装通过，contigs=$(grep -c '^>' asm/contigs.fa)"

echo
echo "ALL TESTS PASSED"
