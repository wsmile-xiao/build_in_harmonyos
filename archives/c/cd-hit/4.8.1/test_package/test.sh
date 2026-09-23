#!/data/service/hnp/bin/bash
# test_package/test.sh — cd-hit 真实功能测试（R34：实际执行被测二进制并校验结果）。
# 在 conanrun 环境内运行（PATH 含安装的 bin/，可解析 cd-hit 二进制）。
# 验证内容：cd-hit 对 3 条微型序列聚类，期望 seq1 与 seq2 同簇、
# seq3 独立，共 2 簇，且 .clstr 输出可校验。
set -euo pipefail

# 注释: 不使用 /tmp（OHOS /tmp 只读），就地使用当前可写目录
TESTDIR="$(pwd)/cdhit-test-run-$$"
mkdir -p "$TESTDIR"
trap 'rm -rf "$TESTDIR"' EXIT

IN="$TESTDIR/in.faa"
OUT="$TESTDIR/out"

cat > "$IN" <<'EOF'
>seq1
AAATTTGGGCCCAAATTTGGGCCC
>seq2
AAATTTGGGCCCAAATTTGGGCC
>seq3
TTTGGGCCCAAATTTGGGCCCAAA
EOF

echo "[test] cd-hit 存在性"
command -v cd-hit >/dev/null 2>&1 || { echo "❌ cd-hit not found in PATH"; exit 1; }

echo "[test] cd-hit 聚类 (3 序列, -c 0.9)"
cd-hit -i "$IN" -o "$OUT" -c 0.9 -n 5 >/dev/null

[ -f "$OUT.clstr" ] || { echo "❌ $OUT.clstr 未生成"; exit 1; }

echo "[test] .clstr 断言"
grep -q '>Cluster 0' "$OUT.clstr" || { echo "❌ Cluster 0 缺失"; exit 1; }
grep -q 'seq1' "$OUT.clstr"       || { echo "❌ seq1 未出现在簇中"; exit 1; }
grep -q 'seq2' "$OUT.clstr"       || { echo "❌ seq2 未出现在簇中"; exit 1; }
grep -q 'seq3' "$OUT.clstr"       || { echo "❌ seq3 未出现在簇中"; exit 1; }

CLUSTERS=$(grep -c '^>Cluster' "$OUT.clstr")
[ "$CLUSTERS" -eq 2 ] || { echo "❌ 期望 2 簇，实际 $CLUSTERS"; exit 1; }

echo "✅ cd-hit 测试通过: $CLUSTERS 簇（seq1+seq2 同簇、seq3 独立）"