#!/bin/sh
# automake 1.19 消费者冒烟四断言（独立测试源文件：CI L0c 要求 test_package/
# 必须有非 conanfile.py 的测试源文件；由 conanfile.py test() 经 sh 绝对路径驱动）。
# 真机 OHOS 内核策略禁 shebang execve，全程解释器前缀 + 绝对路径（见 1.19/notes.md）。
# 用法: sh test.sh <package>/bin
set -e

bindir="${1:?用法: sh test.sh <package>/bin}"
aclocal="$bindir/aclocal"
automake="$bindir/automake"

# 断言在独立临时目录里做（CI #62576 教训）：直接在 $PWD 跑会把
# configure.ac/aclocal.m4/Makefile.in 与 --add-missing 装的 install-sh/
# missing/test-driver 留在 test_package 目录，test_e2e.sh 的 automake
# 向上搜索父目录找到这些残留后"引用而不安装"，导致 E2E 构建目录缺
# install-sh（INSTALL='sh ./install-sh' 找不到文件）。
work="$PWD/test-sh-work.$$"
mkdir -p "$work"
trap 'rm -rf "$work"' EXIT
cd "$work"

# 断言 1/2：工具可执行
sh "$aclocal" --version
echo "[ok] aclocal 可执行"
sh "$automake" --version
echo "[ok] automake 可执行"

# 环境注入核对：ACLOCAL_PATH 是否真的接上
echo "ACLOCAL_PATH=$ACLOCAL_PATH"
echo "PERL5LIB=$PERL5LIB"

# 断言 3：aclocal 在最小 configure.ac 上产出 aclocal.m4（宏目录接对）
cat > configure.ac <<'EOF'
AC_INIT([probe],[0.1])
AM_INIT_AUTOMAKE
AC_CONFIG_FILES([Makefile])
AC_OUTPUT
EOF
sh "$aclocal"
test -f aclocal.m4 || { echo "aclocal 没产出 aclocal.m4 —— 宏路径没接对"; exit 1; }
echo "[ok] aclocal 在真实 configure.ac 上产出了 aclocal.m4"

# 断言 4：automake --add-missing 在真实 Makefile.am 上产出 Makefile.in。
# --add-missing 从 automake 的 libdir 拷贝 install-sh/missing 等辅助文件，
# 实测包装脚本 --libdir 的可重定位逻辑；--copy：OHOS 真机内核策略拒绝
# link() 硬链接（Permission denied），改拷贝模式。
printf 'bin_SCRIPTS = probe\n' > Makefile.am
sh "$automake" --add-missing --copy --foreign
test -f Makefile.in || { echo "automake 没产出 Makefile.in —— libdir 没接对"; exit 1; }
echo "[ok] automake 在真实 Makefile.am 上产出了 Makefile.in"
