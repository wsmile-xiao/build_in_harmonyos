# irqbalance 1.9.4 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-18
- 编译器: clang 15.0.4
- 状态: built（本地验证通过；发布状态以制品仓 upload/CI 为准）

## 编译步骤

```bash
# 1. 获取官方源码（GitHub tag v1.9.4 release tarball）
#    https://github.com/Irqbalance/irqbalance/archive/refs/tags/v1.9.4.tar.gz
#    sha256: f37bb2e27c2e9ec609131d0ee3f770185d3845f79ee6ef11477ea0ffb600a561
# 2. bootstrap（GitHub tag tarball 不含 configure，需 autoreconf）
#    工具链: conan tool_requires automake/1.18 + libtool/2.5.4.1 + autoconf/2.72 + pkgconf
#    ./autogen.sh   # 内部 autoreconf -fv --install
# 3. 平台补丁：config.guess/config.sub 打 HarmonyOS 支持（patch-autotools-ohos.pl）
# 4. configure --prefix=<prefix>  （E136: 修正 configure umask 077→022 + TMPDIR 绝对路径）
# 5. make -j2 && make check（1/1 PASS: runoneshot.sh）&& make install DESTDIR=...
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 直连超时 | 执行端网络无法直连 github.com（gitcode/cnb 可达） | 经环境内已验证的 gh-proxy 官方镜像通道下载 release 归档，与官方 URL 内容 diff 一致后核验 sha256 |
| 2 | config.guess/sub 无法识别 HarmonyOS | autotools 平台识别缺失 | patch-autotools-ohos.pl 注入 HarmonyOS 系统识别与 linux-ohos triplet |
| 3 | config.status: cannot create ./confXXXXXX | HarmonyOS 上 umask 077 + SGID 导致 mktemp 临时目录不可写（E136） | configure 中 umask 077→022，mktemp 使用 $TMPDIR 绝对路径 |
| 4 | aclocal/automake/libtoolize 缺失 | 执行端系统无 automake/libtool | conan tool_requires automake/1.18 + libtool/2.5.4.1，PERL5LIB/ACLOCAL_PATH/_lt_pkgdatadir 指向包内目录 |
| 5 | PKG_CHECK_MODULES 宏未展开 | pkg.m4 未进入 aclocal 搜索路径 | ACLOCAL_PATH 追加 pkg-config share/aclocal（pkg.m4） |
| 6 | undefined symbol: rindex | OHOS libc 无遗留 rindex 符号 | cputree.c 改用标准 strrchr（补丁 0002-cputree.c.patch） |
| 7 | ui/helpers.c: curses.h not found | Makefile.am AM_CFLAGS 未含 $(NCURSESW_CFLAGS) | Makefile.am AM_CFLAGS 追加 NCURSESW_CFLAGS（补丁 0001-Makefile.am.patch） |
| 8 | 测试运行期缺 libglib-2.0.so.0 | make check 时 LD_LIBRARY_PATH 未含 conan glib lib 目录 | 测试环境设置 LD_LIBRARY_PATH 指向 glib 包 lib（配方内由 conanrun 注入） |

## 源码修改

- patches/0001-Makefile.am.patch: AM_CFLAGS 增加 $(NCURSESW_CFLAGS)
- patches/0002-cputree.c.patch: rindex → strrchr
- configure/autogen 生成文件按 E007/E136 在配方 build() 内运行期修补（config.guess/sub HarmonyOS、umask 022、TMPDIR）

## 依赖版本

- glib/2.88.3.1（requirements，制品仓已发布）
- ncurses/6.6（requirements，制品仓已发布）
- tool_requires: automake/1.18, libtool/2.5.4.1, autoconf/2.72, pkgconf/3.0.6

## 验证结果

```bash
# 上游测试（make check，1 个独立上游用例）
# TOTAL: 1  PASS: 1  FAIL: 0
# 消费者验证（test_package）
# irqbalance --version → "irqbalance version 1.9.4"（exit 0）
```
---

**编译结束**: 2026-09-18 21:52
**最终状态**: built
