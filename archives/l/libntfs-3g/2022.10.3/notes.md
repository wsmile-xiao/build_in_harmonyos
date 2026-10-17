# libntfs-3g 2022.10.3 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-10-09
- 编译器: clang 15.0.4 (aarch64-linux-ohos)
- 状态: built

## 编译步骤
上游 git tag tarball（codeload 官方源）不含预生成 configure，需 autogen 自举：

```bash
# 1. 补 m4 宏（configure.ac 引用 AM_PATH_LIBGCRYPT / PKG_CHECK_MODULES）
cp libgcrypt.m4 pkg.m4 -> m4/          # 随配方导出 + ACLOCAL_PATH 注入
# 2. autogen 直跑链（tool_requires automake/1.18 + libtool/2.5.4）
aclocal --force && autoconf -o configure configure.ac \
  && autoheader && libtoolize（补 ltmain.sh）&& automake --add-missing
# 3. E052/E114 修复：移除 configure 中 `umask 077 && mktemp/mkdir` 前缀
sed 's/umask 077 && mktemp/mktemp/g; s/umask 077 && mkdir/mkdir/g' configure
# 4. configure + make + make install DESTDIR
./configure --prefix=$DEFAULT_PREFIX && make && make install DESTDIR=$TEST_PREFIX
# 5. make check（上游无注册测试，无输出）
```

## 遇到问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | autoreconf 报 `possibly undefined macro: AM_PATH_LIBGCRYPT / AC_MSG_ERROR` | configure.ac 引用 libgcrypt.m4/pkg.m4 外部宏，aclocal 搜索路径无定义 | 从 libgcrypt 上游提取 libgcrypt.m4、pkg-config 提取 pkg.m4，随配方导出并注入 ACLOCAL_PATH（同 abiword-plugin-eml 先例） |
| 2 | config.status 报 `can't create ./confXXXXXX/subs1.awk: Permission denied`（E052/E114） | HMDFS 中 `umask 077 && mktemp -d` 创建 2770+setgid 临时目录，owner 也不能写入，chmod 无效 | 移除 configure 内两处 `umask 077 &&` 前缀（E114 同 libgsf 修复）+ TMPDIR 注入 build 内可写目录 |
| 3 | `make install DESTDIR` 报 `mv: .../lib not directory` | 上游 install-exec-hook 将 .so 移至 $DESTDIR/lib，staging 缺该目录 | 预创建 $TEST_PREFIX/lib 再 install（conan autotools.install() 用 prefix=/ 不触发此 hook，无需补丁） |

## 源码修改
无源码 .patch——以上问题均通过配方内构建期处理解决：
- m4 宏随配方导出（recipe 级 m4/ 目录）
- configure 的 umask 077 通过 conanfile.build() 内 `_patch_configure_hmdfs` 修复
- config.guess/config.sub 的 HarmonyOS 识别由 `_patch_config_for_ohos` 注入

## 依赖版本
- automake/1.18（tool_requires，制品仓）
- libtool/2.5.4（tool_requires，制品仓）

## 上游测试清点（R51）
2022.10.3 与 2026.7.7 的测试现状逐项核实一致：**上游无自带测试**。
- 8 个 `Makefile.am` 中 `TESTS` / `check_PROGRAMS` / `check-local` 注册数 = 0
- 仓库树中 `test/` `tests/` `check/` `torture/` 目录数 = 0
- 因此 `make check` 无任何用例可跑（非"跳过"，是上游本就没有）
- 消费者用例由本配方的 `test_package/test.c` 提供（6 条自研断言）
