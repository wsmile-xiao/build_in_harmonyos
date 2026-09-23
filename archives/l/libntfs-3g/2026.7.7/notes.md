# libntfs-3g 2026.7.7 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-15
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

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | autoreconf 报 `possibly undefined macro: AM_PATH_LIBGCRYPT / AC_MSG_ERROR` | configure.ac 引用 libgcrypt.m4/pkg.m4 外部宏，aclocal 搜索路径无定义 | 从 libgcrypt 上游提取 libgcrypt.m4、pkg-config 提取 pkg.m4，随配方导出并注入 ACLOCAL_PATH（同 abiword-plugin-eml 先例） |
| 2 | config.status 报 `can't create ./confXXXXXX/subs1.awk: Permission denied`（E052/E114） | HMDFS 上 `umask 077 && mktemp -d` 创建 2770+setgid 临时目录，owner 也不能写入，chmod 无效 | 移除 configure 内两处 `umask 077 &&` 前缀（E114 同 libgsf 修复）+ TMPDIR 注入 build 内可写目录 |
| 3 | `make install DESTDIR` 报 `mv: .../lib not directory` | 上游 install-exec-hook 将 .so 移至 $DESTDIR/lib，staging 缺该目录 | 预创建 $TEST_PREFIX/lib 再 install（conan autotools.install() 用 prefix=/ 不触发此 hook，无需补丁） |

## 源码修改
无源码 .patch——以上问题均通过配方内构建期处理解决：
- m4 宏随配方导出（recipe 级 m4/ 目录）
- configure 的 umask 077 通过 conanfile.build() 内 `_patch_configure_hmdfs` 修复

## 依赖版本
- automake/1.18（tool_requires，制品仓）
- libtool/2.5.4（tool_requires，制品仓）
- libgcrypt.m4（从 libgcrypt-1.11.0 release 提取，仅供 configure 宏展开，非运行依赖）
- 运行时依赖：无（fuse=internal 内嵌 libfuse-lite；crypto gcrypt/gnutls、uuid 为可选，缺失自动降级）

## 验证结果
- configure + make 编译通过（libntfs-3g.so.90.0.0 / libntfs-3g.a / ntfs-3g、lowntfs-3g、ntfsprogs 工具集）
- make install DESTDIR 安装成功
- make check 通过（上游无注册测试用例，R51 证据：Makefile.am 无 TESTS；GitHub 仓库树无 test 路径；configure.ac 无测试钩子）
- test_package 自研 4 项断言（ntfs_malloc/ntfs_free 内存路径 + 版本宏）

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | autotools 配方：autogen 直跑链 + E052/E114 修复 + ELF 重签名 |
| conandata.yml | 上游官方 codeload 源 + sha256 |
| test_package/ | 自研消费者测试（4 断言）+ MANIFEST.yml |
| commands.json | 软件级命令行工具声明（ntfs-3g/ntfsprogs 工具集） |

## 注意事项
- 上游依赖检查：crypto 需 gcrypt+gnutls 同时存在才编译（缺失仅 degrade 不报错）；uuid 为可选（--without-uuid 或缺失降级）
- fuse 驱动默认 internal（linux*|solaris* 平台），无外部 fuse 依赖
- 适配路径：路径 A（基础适配）

## 适配完整性说明（W4 审计 P3-5/R40）
libntfs-3g 属文件系统底层库，本次为**构建级适配**（autogen 自举、
config.guess OHOS 三元组识别、E052/E114 umask 修复、ELF 重签名），
test_package 覆盖库可链接性、公开内存管理 API（ntfs_malloc/ntfs_free）
与版本头文件可用性。上游无自带测试（R51 已如实申报），NTFS 卷真实
读写路径（挂载/元数据解析）依赖内核 FUSE 能力与真实 NTFS 镜像，超出
基础适配（路径 A）验证范围，留待设备侧真机挂载验证或后续深度适配
（路径 B）补充。
---

**编译结束**: 2026-09-15 11:49
**最终状态**: built
