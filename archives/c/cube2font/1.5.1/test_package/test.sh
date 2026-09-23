#!/data/service/hnp/bin/bash
# test_package/test.sh — cube2font 真实转换消费者测试
#
# 在 conanrun 环境执行（PATH 含已安装 bin/，LD_LIBRARY_PATH 含 freetype 依赖库）。
# 上游没有测试套件，因此本脚本构造真实输入、以真实产物为判据，覆盖
# FreeType 光栅化 → zlib deflate/CRC32 → PNG 纹理页 → .cfg 字符表全链路：
#   1) 生成覆盖 Cube 引擎字符集的最小 TrueType 字体（不依赖设备字体）
#   2) 按上游 man 页文档化的调用形态跑两次真实转换（单页 / 多页带描边）
#   3) 解压 PNG 纹理逐像素核对，并核对 .cfg 字符表与纹理页的一致性
set -eu

HERE="$(cd "$(dirname "$0")" && pwd)"
D="${1:-$PWD}/cube2font-test"
PY="${PYTHON:-python3}"
CHARS=249          # cube2font 内建字符集 iscubeprint() 的字符数

rm -rf "$D"
mkdir -p "$D"

echo "[test] 1/4 参数契约：缺参数必须以非零码退出并打印 usage"
if cube2font > "$D/usage.txt" 2>&1; then
    echo "❌ cube2font 无参数时返回 0"
    exit 1
fi
grep -q '^Usage: cube2font infile outfile' "$D/usage.txt" || {
    echo "❌ 缺少 usage 输出"; cat "$D/usage.txt"; exit 1; }
echo "✅ usage 契约 OK"

echo "[test] 2/4 生成最小 TTF 测试字体（覆盖 Cube 字符集）"
"$PY" "$HERE/make_test_font.py" "$D/testfont.ttf"
test -s "$D/testfont.ttf" || { echo "❌ 测试字体未生成"; exit 1; }

echo "[test] 3/4 默认参数单页转换：cube2font testfont.ttf plain 0 1 0 0 16 16 256 256"
cube2font "$D/testfont.ttf" "$D/plain" 0 1 0 0 16 16 256 256
"$PY" "$HERE/check_output.py" "$D/plain.cfg" "$CHARS" --exact

echo "[test] 4/4 描边多页转换：cube2font testfont.ttf bordered 3 19 1 1 49 49 512 512 32 64"
cube2font "$D/testfont.ttf" "$D/bordered" 3 19 1 1 49 49 512 512 32 64
"$PY" "$HERE/check_output.py" "$D/bordered.cfg" "$CHARS"

echo "✅ cube2font test_package PASSED"
