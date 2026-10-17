# libvpd 2.2.11 适配笔记（HarmonyOS PC aarch64）

## 编译环境
- 构建系统: autotools（官方 tag 不携带生成的 configure，需 bootstrap）
- 编译日期: 2026-09-27
- 编译器: clang/clang++ 15（OHOS SDK 26.0.0.18，aarch64-linux-ohos）
- 状态: built（conan create 本地 W3 通过）

## 编译步骤
1. `curl -L https://codeload.github.com/power-ras/libvpd/tar.gz/refs/tags/v2.2.11` 获取官方 tag 源码；
   SHA-256=`557a5ead6d15d4f5a6d0e3d0ac0344cc028e17a162d9174680d41b37c99b1431`。
2. conan 配方内 bootstrap：`aclocal`（ACLOCAL_PATH 指向 libtool 包 share/aclocal）
   + 拷贝 `libtool/share/libtool/build-aux/ltmain.sh` 到 `config/`
   + `autoheader` + `automake --add-missing --copy` + `autoconf`。
3. `./configure --build=aarch64-linux-gnu --host=aarch64-linux-ohos`
   CPPFLAGS 固化 `-I<src>/src` 与 sqlite3 头路径；`make -j1`；`make install`。
4. `conan create`（profile ohos-aarch64）构建 libvpd 与 libvpd_cxx 双库（共享+静态），
   test_package 真实消费者用例如下：LSVPD::System pack/unpack 往返 + C API
   new_vpdretriever 调用，ctest 1/1 通过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 官方 tag 无 configure，`./bootstrap.sh` 依赖 libtoolize 但 conan libtool 包 pkgauxdir 烘焙成 `//share/libtool` | 包不可重定位 | 配方内跳过 libtoolize：手动拷贝 ltmain.sh + 用 ACLOCAL_PATH 提供 libtool.m4 |
| 2 | conan 环境 PERL5LIB 前置 ohpcd perl/5.42.2 模块，与 automake 脚本 shebang 的系统 perl（5.42.0）XS ABI 不兼容（`Perl_my_cxt_init: symbol not found`/`strict.pm` 缺失）| 双 perl 解释器冲突；autoconf 包 autom4te/autoconf/autoheader shebang 硬编码 conan perl 且 `//share/autoconf` 前缀损坏 | 构建目录生成 wrapper：以系统 perl 执行 `.autom4te-real/.autoconf-real/.autoheader-real`，导出 `autom4te_perllibdir`/`AC_MACRODIR`/`AUTOM4TE_CFG`（指向修正后的 autom4te.cfg），并用 `AUTOM4TE`/`AUTOCONF`/`AUTOHEADER` 环境变量钉住 |
| 3 | config.status `can't create ./confXXXX/subs1.awk: Permission denied` | HMFS 将 umask 077 的 0700 临时目录归一化为 0760（组无 x），进程以 group 身份访问无法建文件 | build() 内 `sed -i 's/umask 077/umask 002/g' config.status` 后重跑（POSIX 正确 FS 上为 no-op）|
| 4 | C++ 库链接失败 `unable to find library -lstdc++` | OHOS clang 无 libstdc++，C++ 运行时为 libc++（clang++ 自动链接） | 补丁移除 `libvpd_cxx_la_LDFLAGS` 中冗余 `-lstdc++` |
| 5 | `make install` 失败 `install: No such file or directory` | OHOS 构建环境无 coreutils `install`；install-exec-hook 还安装无关 udev 规则 | 补丁将 install-exec-hook 改为空转（udev/vpdupdate 规则不适用 OHOS）|
| 6 | 异目录构建 `-I./src/` 失效，`<libvpd-2/*.hpp>` 找不到 | 上游 AM_CPPFLAGS 为 cwd 相对路径，conan 的 make 运行目录与源码目录不同 | configure 参数固化绝对 `CPPFLAGS=-I<src>/src`（含 sqlite3 头）|
| 7 | W3 JC 门禁 full 模式扫到其他库既有基线杂物（cloog/.build-closed 等） | 本地分支无提交时 junk_check 回退 `git ls-files` 整仓扫描 | 按基线隔离复验规则记录/隔离/复跑/原样恢复（SHA-256 pre==post），提交本库后 JC 以 incremental diff 模式只查本库 |

## 源码修改
- patches/0001-makefile-am-ohos-adapt.patch：移除 `-lstdc++`；install-exec-hook 空转。

## 依赖版本
- sqlite3/3.53.4（configure 硬性要求，已在 ohpcd 发布）
- tool_requires: automake/1.18, libtool/2.5.4, autoconf/2.72, m4/1.4.19, perl/5.42.2

## 验证结果
- `conan create`（test_package 消费者测试 1/1 通过，RC=0）
- 消费者验证：consumer_c（C API new_vpdretriever 调用并释放）、
  consumer_cpp（System pack/unpack 往返 454 字节一致性断言）全部通过
- HarmonyOS 专项测试：`__OHOS__` 编译期断言 + uname 平台打印 +
  dlopen(libvpd.so)+dlsym(new_vpdretriever) + System pack/unpack 往返 — ALL PASS
- 上游测试统计：上游 tag 源码无任何测试套件（无 tests/ 目录、Makefile.am 无
  TESTS/check_PROGRAMS，`make check` 空转），source_declared_total=0

## 上游测试台账（双口径）
- 源码声明总数：0（官方 v2.2.11 tag 未携带测试套件；
  已枚举：顶层无 tests/、src/ 无测试源文件、Makefile.am 无 TESTS/check_PROGRAMS、
  libvpd-ci/ 仅为 docker 构建脚本）
- 当前配置可执行用例数：0；实际执行通过：0；失败 0；未实例化 0
- 鸿蒙专项测试 + 消费者验证见 tests/ 目录（consumer_c.c、consumer_cpp.cpp、
  ohos_specific_test.cpp、run_tests.sh）

## 注意事项
- 跨库可复用知识：HMFS umask-077 临时目录归一化（config.status 修复模式）、
  ohpcd autoconf/automake/perl 工具包解释器与路径不可重定位（wrapper 统一系统
  perl 模式）、conan 异目录构建 -I 相对路径固化模式。详见知识候选台账。
---

**编译结束**: 2026-09-27 22:24
**最终状态**: built
