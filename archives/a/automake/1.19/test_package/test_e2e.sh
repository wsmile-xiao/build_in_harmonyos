#!/bin/sh
# automake 1.19 完整消费者端到端用例（鸿蒙特有测试）
#
# 下游微型 autotools 工程 e2e-probe（fixture：configure.ac / Makefile.am /
# probe / configure，其中 configure 为发布式随档脚本，真机无 autoconf），
# 用被测包内 aclocal/automake 走通全链路：
#   aclocal → automake --add-missing --copy → sh ./configure --prefix
#   → make → make check → make install → 运行已安装产物 probe 并核对输出
#
# 真机适配要点（与 notes.md「适配技术难点」一致）：
#   - OHOS 内核拒绝 shebang execve，所有脚本一律 sh 前缀；
#   - make 规则内的 INSTALL 系列已由 configure 替换为 'sh ./install-sh'；
#   - LOG_COMPILER=sh（Makefile.am fixture）让 make check 的并行
#     harness 经 sh 执行 probe——不能用 TESTS_ENVIRONMENT=sh，它在
#     parallel harness 里会被拼到 LOG_DRIVER 前，展开成
#     "sh /bin/sh ./test-driver"（sh 把二进制 /bin/sh 当脚本执行）；
#   - LOG_DRIVER 由 automake 生成为 $(SHELL) ./test-driver，天然 sh 驱动。
#
# 用法: sh test_e2e.sh <package>/bin
set -e

bindir="${1:?用法: sh test_e2e.sh <package>/bin}"
aclocal="$bindir/aclocal"
automake="$bindir/automake"
# 绝对路径化：脚本随后 cd 进构建目录，相对 srcdir 会失效——辅助文件
# 兜底拷贝与 fixture 定位都依赖它（相对路径调用实测复现 CI #62576）。
srcdir=$(cd "$(dirname "$0")" && pwd)
fixture="$srcdir/e2e-probe"

work="$PWD/e2e-work.$$"
mkdir -p "$work"
trap 'rm -rf "$work"' EXIT

cp "$fixture/configure.ac" "$fixture/Makefile.am" \
   "$fixture/probe" "$fixture/configure" "$work/"
cd "$work"

# 供 make 因时间戳重建时与 configure 继承（sh 前缀绝对路径）
export ACLOCAL="sh $aclocal"
export AUTOMAKE="sh $automake"

# 1) aclocal：消费 configure.ac（AC_INIT/AM_INIT_AUTOMAKE 宏展开）
sh "$aclocal" -I .

# 2) automake：生成 Makefile.in，--add-missing 从包 libdir 拷贝
#    install-sh / missing 等辅助脚本
sh "$automake" --add-missing --copy --foreign

# 兜底（CI #62576 教训）：automake 的缺失文件搜索会向上查父目录——若
# test_package 目录里已有 install-sh/missing/test-driver 残留（同目录
# test.sh 直跑过、或任何祖先污染），automake 会"引用而不安装"，构建目录
# 里就没有 install-sh，make install 的 INSTALL='sh ./install-sh' 报
# No such file。这里把三件套确保落到当前目录（automake 已装则跳过）。
for aux in install-sh missing test-driver; do
    [ -f "$aux" ] || cp "$srcdir/$aux" "$aux" 2>/dev/null || true
done

# 关键：发行 tarball 时间戳惯例——configure 必须比 configure.ac 与
# aclocal.m4 新，否则 make 的 `configure: configure.ac aclocal.m4`
# 重生成规则会用环境里的真 autoconf（真机 /data/service/hnp 有 2.72）
# 覆盖发布式 configure，后续 config.status 机制在 OHOS 上必炸。
touch configure

# 3) configure：消费 Makefile.in 生成 Makefile（发布式随档脚本）
sh ./configure --prefix="$work/prefix"

# 4) make：真实构建
make

# 5) make check：TESTS=probe 经 LOG_COMPILER=sh（Makefile.am fixture）
#    实跑产物——parallel harness 经 sh 驱动 probe
make check 2>&1 | tee check.log
grep -q "PASS: probe" check.log

# 6) make install：bin_SCRIPTS 经 INSTALL='sh ./install-sh' 装入 prefix/bin
make install

# 7) 运行已安装产物并核对输出
out=$(sh "$work/prefix/bin/probe")
if [ "$out" != "probe-ok 1.0" ]; then
    echo "probe 输出不符: $out"
    exit 1
fi

echo "[ok] 端到端消费者用例全链路通过: aclocal→automake→configure→make→make check→make install→运行 probe"
