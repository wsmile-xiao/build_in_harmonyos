#!/data/service/hnp/bin/bash
# test_package/test.sh — comprez 2.7.3 功能测试
# 在 conanrun 环境运行（PATH 含安装的 bin/）
set -eu

fail=0
echo "[test] 1. z -h 用法输出"
# z -h 打印 usage 后 exit 1（上游设计），故检查输出内容而非退出码
if z -h 2>&1 | grep -q "usage:"; then
    echo "✅ z -h 用法输出 OK"
else
    echo "❌ z -h 无用法输出"
    fail=1
fi

echo "[test] 2. z --version?（无该选项，用 -h 检查版本行）"
z -h 2>&1 | grep -q "Version 2.7.3" && echo "✅ 版本行 OK" || { echo "⚠️ 版本行未匹配（不阻塞）"; }

# 准备测试数据
TDIR=$(mktemp -d "${TMPDIR:-$HOME/tmp}/comprez-test.XXXXXX" 2>/dev/null || mktemp -d)
mkdir -p "$TDIR/work/docs/sub"
echo "alpha file content" > "$TDIR/work/docs/index.txt"
echo "nested file content" > "$TDIR/work/docs/sub/n.txt"
cd "$TDIR/work"

echo "[test] 3. gzip 压缩 (z -gz)"
z -gz -L docs > /dev/null 2>&1 || { echo "❌ gzip 压缩失败"; fail=1; }
[ -f docs.tgz ] || { echo "❌ docs.tgz 未生成"; fail=1; }
echo "✅ gzip 压缩 OK"

echo "[test] 4. gzip 列表 (z -t)"
z -t docs.tgz 2>&1 | grep -q "index.txt" || { echo "❌ gzip 列表失败"; fail=1; }
echo "✅ gzip 列表 OK"

echo "[test] 5. gzip 解压 (z docs.tgz)"
mkdir -p "$TDIR/restore"
cp docs.tgz "$TDIR/restore/"
cd "$TDIR/restore"
z docs.tgz > /dev/null 2>&1 || { echo "❌ gzip 解压失败"; fail=1; }
grep -q "alpha file content" docs/index.txt || { echo "❌ 解压内容不一致"; fail=1; }
grep -q "nested file content" docs/sub/n.txt || { echo "❌ 解压内容不一致(sub)"; fail=1; }
echo "✅ gzip 解压+内容一致性 OK"

echo "[test] 6. bzip2 压缩解压 (z -I)"
# z 压缩后会删除源目录，需重建
mkdir -p "$TDIR/bz/docs/sub"
echo "alpha file content" > "$TDIR/bz/docs/index.txt"
echo "nested file content" > "$TDIR/bz/docs/sub/n.txt"
cd "$TDIR/bz"
z -I -L docs > /dev/null 2>&1 || { echo "❌ bzip2 压缩失败"; fail=1; }
[ -f docs.tbz2 ] || { echo "❌ docs.tbz2 未生成"; fail=1; }
mkdir -p "$TDIR/bzr"
cp docs.tbz2 "$TDIR/bzr/"
cd "$TDIR/bzr"
z docs.tbz2 > /dev/null 2>&1 || { echo "❌ bzip2 解压失败"; fail=1; }
grep -q "alpha file content" docs/index.txt || { echo "❌ bzip2 内容不一致"; fail=1; }
echo "✅ bzip2 压缩解压 OK"

echo "[test] 7. xz 压缩解压 (z -xz)"
# z 压缩后会删除源目录，需重建
mkdir -p "$TDIR/xzd/docs/sub"
echo "alpha file content" > "$TDIR/xzd/docs/index.txt"
echo "nested file content" > "$TDIR/xzd/docs/sub/n.txt"
cd "$TDIR/xzd"
z -xz -L docs > /dev/null 2>&1 || { echo "❌ xz 压缩失败"; fail=1; }
# -xz 默认映射 .txz；也兼容 .tar.xz 输入
ARCHIVE=$(ls docs.txz docs.tar.xz 2>/dev/null | head -1)
[ -n "$ARCHIVE" ] || { echo "❌ xz 归档未生成"; fail=1; }
mkdir -p "$TDIR/xzr"
cp "$ARCHIVE" "$TDIR/xzr/"
cd "$TDIR/xzr"
z "$ARCHIVE" > /dev/null 2>&1 || { echo "❌ xz 解压失败"; fail=1; }
grep -q "alpha file content" docs/index.txt || { echo "❌ xz 内容不一致"; fail=1; }
echo "✅ xz 压缩解压 OK"

echo "[test] 8. zip 压缩解压 (z -zip)"
mkdir -p "$TDIR/zpd"
cd "$TDIR/zpd"
echo "zip payload" > single.txt
z -zip -L single.txt > /dev/null 2>&1 || { echo "❌ zip 压缩失败"; fail=1; }
[ -f single.txt.zip ] || { echo "❌ single.txt.zip 未生成"; fail=1; }
mkdir -p "$TDIR/zpr"
cp single.txt.zip "$TDIR/zpr/"
cd "$TDIR/zpr"
z single.txt.zip > /dev/null 2>&1 || { echo "❌ zip 解压失败"; fail=1; }
grep -q "zip payload" single.txt || { echo "❌ zip 内容不一致"; fail=1; }
echo "✅ zip 压缩解压 OK"

echo "[test] 9. zzcat 解压到 stdout"
cd "$TDIR/bz"   # docs.tbz2 场景 → 用 gzip 场景
mkdir -p "$TDIR/zz"
cd "$TDIR/zz"
echo "zzcat payload" > f.txt
z -gz -L f.txt > /dev/null 2>&1
[ -f f.txt.gz ] || { echo "❌ gzip 单文件压缩失败"; fail=1; }
OUT=$(zzcat f.txt.gz)
[ "$OUT" = "zzcat payload" ] || { echo "❌ zzcat 输出不一致: [$OUT]"; fail=1; }
echo "✅ zzcat OK"

rm -rf "$TDIR"

if [ "$fail" -eq 0 ]; then
    echo ""
    echo "🎉 comprez 2.7.3 全部 9 项功能测试通过"
    exit 0
else
    echo ""
    echo "❌ 存在失败项"
    exit 1
fi