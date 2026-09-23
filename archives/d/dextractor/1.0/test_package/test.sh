#!/data/service/hnp/bin/bash
# test_package/test.sh — DEXTRACTOR 1.0 功能验证（运行于 conanrun 环境）
#
# 覆盖:
#   T1  fasta → dexta → undexta 往返（字节级一致）——验证 2-bit 压缩编码器
#   T2  quiva → dexqv → undexqv 往返（头+4 条 QV 流无损，delTag 按上游 2-bit 设计重建）
#   T3  dexta/undexta 错误路径（无参/非法选项/缺文件）
#   T4  dextract（HDF5 工具）在目标平台运行时验证：
#       主程序入口首先调用 H5Zfilter_avail(H5Z_FILTER_DEFLATE)，
#       只有 libhdf5.so 动态加载成功且 zlib deflate 滤镜可用才会走到 Usage 分支
#       —— 对应 HarmonyOS 平台的动态加载/链接适配点（rule12 鸿蒙特有测试）。
set -eu

WORK="$(mktemp -d "${TMPDIR:-/tmp}/dextractor-test.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT
cd "$WORK"

fail() { echo "FAIL: $1" >&2; exit 1; }
ok()   { echo "PASS: $1"; }

# ─────────────────────────────────────────────────────────────────────────────
# T1: fasta → dexta → undexta 往返
# ─────────────────────────────────────────────────────────────────────────────
python3 - <<'PYEOF' > sample.fasta
seq1 = 'acgt' * 30
seq2 = 'tgca' * 20
with open('sample.fasta', 'w') as f:
    f.write('>sample/1/0_120 RQ=0.750\n')
    f.write(seq1[:80] + '\n' + seq1[80:] + '\n')
    f.write('>sample/2/0_80 RQ=0.800\n')
    f.write(seq2 + '\n')
PYEOF
cp sample.fasta sample.orig
dexta -k sample.fasta        || fail "T1 dexta 压缩失败"
undexta sample.dexta          || fail "T1 undexta 解压失败"
cmp -s sample.orig sample.fasta || fail "T1 fasta 往返字节不一致"
ok "T1 fasta 往返字节级一致 (dexta/undexta)"

# ─────────────────────────────────────────────────────────────────────────────
# T2: quiva → dexqv → undexqv 往返
#     dexqv 按上游设计: delQV/insQV/mergeQV/subQV 与头行无损(Huffman)，
#     delTag 以 2-bit 编码有损重建(非 ACGT → 'a'，run 位 → 'n')
# ─────────────────────────────────────────────────────────────────────────────
python3 - <<'PYEOF'
import random
random.seed(42)
L = 3000
def qv():
    return ''.join(chr(random.randint(33, 126)) for _ in range(L))
tag = ''.join(random.choice('NI DSI DSNDIDSN') for _ in range(L))
entries = [
    ('@sample/1/0_%d RQ=0.750' % L, qv(), tag, qv(), qv(), qv()),
    ('@sample/2/0_%d RQ=0.800' % L, qv(), tag, qv(), qv(), qv()),
]
with open('sample.quiva', 'w') as f:
    for e in entries:
        f.write('\n'.join(e) + '\n')
PYEOF
cp sample.quiva sample.orig
dexqv -k sample.quiva         || fail "T2 dexqv 压缩失败"
undexqv sample.dexqv           || fail "T2 undexqv 解压失败"

python3 - <<'PYEOF'
import sys

o = open('sample.orig').read().splitlines()
r = open('sample.quiva').read().splitlines()

# 全局 run char: 上游 QVcoding_Scan 按扫描顺序首次遇到 'N'/'n' 即固定
delChar = None
for e in range(len(o) // 6):
    base = e * 6
    for k, ch in enumerate(o[base + 2]):
        if ch in 'Nn':
            delChar = o[base + 1][k]
            break
    if delChar is not None:
        break

def number_read(c):
    return {'A': 0, 'C': 1, 'G': 2, 'T': 3}.get(c.upper(), 0)

LETTERS = 'acgt'

def expected_tag(delqv, tag):
    if delChar is None:
        return ''.join(LETTERS[number_read(c)] for c in tag)
    return ''.join('n' if delqv[k] == delChar else LETTERS[number_read(c)]
                   for k, c in enumerate(tag))

# 无损流: 每条 entry 的头/delQV/insQV/mergeQV/subQV (行 1,2,4,5,6 / 7,8,10,11,12)
lossless = (1, 2, 4, 5, 6, 7, 8, 10, 11, 12)
for ln in lossless:
    if o[ln - 1] != r[ln - 1]:
        sys.exit('T2 quiva 无损流不一致: 行 %d' % ln)
print('OK quiva 无损流 10 行逐行一致')

# delTag 流: 行 3 与 9 按全局 delChar 重建
for entry in (1, 2):
    base = (entry - 1) * 6
    exp = expected_tag(o[base + 1], o[base + 2])
    if r[base + 2] != exp:
        sys.exit('T2 quiva delTag 重建不一致: entry %d' % entry)
print('OK quiva delTag 2 行符合预期重建')
PYEOF
ok "T2 quiva 往返 (无损流 + delTag 重建)"

# ─────────────────────────────────────────────────────────────────────────────
# T3: 错误路径
# ─────────────────────────────────────────────────────────────────────────────
set +e
dexta >/dev/null 2>err.log
rc=$?
set -e
[ "$rc" -eq 1 ] || fail "T3 dexta 无参退出码=$rc (期望 1)"
grep -q "Usage: dexta" err.log || fail "T3 dexta 无参未打印 Usage"
ok "T3a dexta 无参 → rc=1 + Usage"

set +e
dexta -x sample.fasta >/dev/null 2>err.log
rc=$?
set -e
[ "$rc" -eq 1 ] || fail "T3 dexta 非法选项退出码=$rc (期望 1)"
grep -q "illegal option" err.log || fail "T3 dexta 非法选项未报错"
ok "T3b dexta 非法选项 → rc=1"

set +e
dexta missing.fasta >/dev/null 2>err.log
rc=$?
set -e
[ "$rc" -eq 1 ] || fail "T3 dexta 缺文件退出码=$rc (期望 1)"
grep -q "Cannot open" err.log || fail "T3 dexta 缺文件未报错"
ok "T3c dexta 缺文件 → rc=1"

# ─────────────────────────────────────────────────────────────────────────────
# T4: dextract（HDF5 工具）目标平台运行时验证（鸿蒙特有测试）
#     主程序入口先执行 H5Zfilter_avail(H5Z_FILTER_DEFLATE):
#       - libhdf5.so 无法加载          → 进程启动失败 (rc!=1) → 本断言失败
#       - zlib deflate 滤镜不可用      → 打印 "zlib library is not present" → grep 失败
#       - 动态加载 + zlib 滤镜均 OK    → 走到 Usage 分支 → rc=1 且 stderr 含 "Usage: dextract"
#     注：上游 ARG_NON_NEGATIVE 宏要求选项值紧贴选项（-l10），分离写法
#         (-l 10) 会走 "argument is not an integer" 提前 exit(1)。
# ─────────────────────────────────────────────────────────────────────────────
set +e
dextract -l10 >/dev/null 2>err.log
rc=$?
set -e
[ "$rc" -eq 1 ] || fail "T4 dextract 退出码=$rc (期望 1; 检查 libhdf5.so 是否成功动态加载)"
grep -q "Usage: dextract" err.log || fail "T4 dextract 未走到 Usage 分支 (HDF5/zlib 运行时检查失败)"
ok "T4 dextract 运行时: libhdf5.so 动态加载 + zlib deflate 滤镜可用 (鸿蒙特有)"

echo
echo "ALL TESTS PASSED"
