# libhbalinux 1.0.16 适配笔记

## 编译环境
- 构建系统: 上游 autotools（**只有源码与 `configure.ac`/`Makefile.am`，无生成的 configure**；
  tarball 里名为 `CONFIGURE` 的文件实际是通用 INSTALL 文本）
- 编译日期: 2026-09-22
- 编译器: OHOS clang 15.0.4（Conan profile `ohos-aarch64`，OHOS SDK 26.0.0.18）
- 依赖: libpciaccess/0.19（链入 DSO）、libhbaapi/2.2.9（头文件）、zlib/1.3.1.2（override，PIC）
- 构建工具: automake/1.18、libtool/2.5.4（tool_requires）；autoconf/autoreconf/pkg-config/perl 取环境
- 状态: built

## 版本与源码
- 平台版本 `1.0.16` == Debian `libhbalinux_1.0.16.orig.tar.gz`（upstream 1.0.16 即最终版本）
- sha256 `e0d8fabcd8a74d76a8f768eb1dfedadbe0c71b3d55bfc255c8cdd74176c150f6`（42605 B；`tar tzf` 28 条目录项 = 1 目录 + 27 文件）
- 上游官方下载已下线（`downloads.open-fcoe.org` NXDOMAIN、`www.open-fcoe.org/openfc/...` 404、
  GitHub 无官方仓库）→ 与 `libhbaapi/2.2.9` 相同，使用 Debian pool 的 upstream orig tarball

## 产物
- `lib/libhbalinux.so.2.0.2`（soname `libhbalinux.so.2`）+ 软链 `.so.2`、`.so`
- `lib/pkgconfig/libhbalinux.pc`（prefix 已重写为包目录）
- `licenses/COPYING`（LGPL-2.1）
- 已删除 libtool `.la`；`DT_NEEDED` 仅 `libc.so`（pciaccess/zlib 静态并入）
- 上游不安装任何头文件（无 `include/`）

## 构建要素

```sh
autoreconf --install --force            # 生成 configure/Makefile.in/aclocal.m4（tool_requires: automake+libtool）
# 程序化放宽 autoreconf 产物里的 umask 077 -> 022（E011）
# 程序化生成 pciaccess.pc 别名（PkgConfigDeps 只产出 libpciaccess.pc）
./configure --build=aarch64-unknown-linux-gnu --host=aarch64-linux-ohos   # E007
make -j2
make install                            # install-data-hook 在 OHOS 上仅打印 hba.conf 警告
```

| # | 问题 | 原因 | 处理 |
|---|------|------|------|
| 1 | 无 `configure`/`Makefile.in`/`aclocal.m4` | 上游只发源码 | `autoreconf --install --force` |
| 2 | `checking for pciaccess... no` → `Package requirements (pciaccess) were not met` | `configure.ac:9` 查模块名 `pciaccess`；libpciaccess/0.19 未设 `pkg_config_name`，PkgConfigDeps 只产出 `libpciaccess.pc` | `generate()` 生成 `pciaccess.pc` 别名（xf86-video-r128 先例） |
| 3 | `ld.lld: error: relocation R_AARCH64_ADR_PREL_PG_HI21 cannot be used against symbol 'z_errmsg'; recompile with -fPIC` | libpciaccess 传递依赖 zlib/1.3.1 的静态 `libz.a` 非 PIC | `self.requires("zlib/1.3.1.2", override=True)`（E541；zlib 仍静态，避免与系统 libz.so 冲突） |
| 4 | `config.status: error: could not setup config files machinery` / `subs1.awk: Permission denied` | autoreconf 生成的 `configure` 用 `umask 077 && mktemp -d`，HMDFS setgid 下 0700 目录不可写（**E011**） | `build()` 在 autoreconf 后程序化 `umask 077` → `022` |
| 5 | `configure: error: cannot guess build type` | `config.guess` 在 HMDFS 上无法创建临时文件（**E007**） | `generate()` 显式传 `--build=aarch64-unknown-linux-gnu --host=aarch64-linux-ohos` |
| 6 | `** WARNING: <prefix>/etc/hba.conf does not exist` | 上游 `install-data-hook` 想把 vendor 库路径追加进 `${sysconfdir}/hba.conf`；OHOS /etc 只读且无该文件 | 上游脚本自身容错：仅打印警告，不失败 |
| 7 | `Imported target "libhbalinux::libhbalinux" includes non-existent path .../include` | 本库不安装头文件，Conan 默认 `includedirs=["include"]` | `package_info()` 中 `self.cpp_info.includedirs = []` |
| 8 | 复核构建时 `autoreconf` 报 `configure.ac:4: error: possibly undefined macro: AM_INIT_AUTOMAKE` / `autoconf failed`，生成的 `configure` 里残留裸宏 | `refresh-patch --auto`（finish Step 1）会在**基线目录**写入 0 字节占位文件（`aclocal.m4`、`Makefile.in`、`configure~`、`config.guess` 等）；`autoreconf` 一旦发现 `aclocal.m4` 存在且首行不是 `generated ... by aclocal`，就**跳过 aclocal**（autoreconf 源码: `$uses_aclocal = 0 unless /generated.*by aclocal/`）→ automake/libtool 宏未展开 | 从 tarball 重建 pristine 基线目录后继续；同时删除该步误生成的 12 个"生成文件"补丁（R6：不改生成文件），本包 `patches/` 保持 0 个。**注意**：`conan create`/CI 直接从 conandata URL 取源码，不受影响（G2/W3 全程通过） |

## 依赖语义（决定 test_package 写法）

- `Makefile.am:1 AM_CFLAGS = $(HBAAPI_CFLAGS) $(PCIACCESS_CFLAGS)`、`:9 LIBADD = $(PCIACCESS_LIBS)`
  ⇒ **HBAAPI 只提供头文件**（`AC_SUBST` 未导出 `HBAAPI_LIBS`），**pciaccess 参与链接**。
- 本库是 SNIA HBAAPI 的 **vendor 库**：libHBAAPI 通过 `/etc/hba.conf` 动态加载它，调用其导出的
  `HBA_RegisterLibrary(V2)` 取回处理函数表（`vendor_lib_entrypoints`），随后调用这些 handler。
- 适配器信息来源：`/sys/class/fc_host`（`adapt_impl.h:22`）、`/sys/class/fc_remote_ports`、
  `/sys/class/scsi_device`、`/sys/class/net`；sysfs 缺失时才用 libpciaccess。

## 上游测试核验（R51 三步法）

1. **清点**：`tar tzf libhbalinux_1.0.16.orig.tar.gz` = 28 条目录项（1 目录 + 27 文件），**无** `test/`、`tests/`；无 `CHANGELOG`/`NEWS`。
2. **注册目标**：`grep -nE 'TESTS|check_PROGRAMS|check-local|BUILD_TESTING|pytest' Makefile.am configure.ac` → **rc=1（无匹配）**；
   `Makefile.am` 仅有 `lib_LTLIBRARIES` / `pkgconfig_DATA` / `install-data-hook`；无 `make check`。
3. **可运行上游路径**：仅 `install-data-hook`（安装期脚本），已在 `make install` 中真实执行（见问题 6 的日志原文）。
   SNIA 样例程序 `hbaapitest`/`hbasample` 属于 **libHBAAPI** 工程（`libhbaapi/2.2.9` 已适配并执行留证），
   本库 tarball 内不存在。
⇒ 上游测试用例数 **0**（无自动化测试、无样例程序），如实申报；不以下游 test_package 冒充上游统计。

## 消费者测试（test_package，11 条断言，其中 OHOS 专属 3 条）

`test_package/test_libhbalinux.c`（仅用安装后的产物；先包 `<time.h>` 规避上游 hbaapi.h 的 struct tm 怪癖）：

1. `case1` `HBA_RegisterLibraryV2()` 返回 OK 且填回关键 handler
2. `case2` `GetVersionHandler() == HBA_LIBVERSION`(2)
3. `case3` `LoadLibraryHandler() == HBA_STATUS_OK`（adapter_init 扫 sysfs）
4. `case4` 无 `/sys/class/fc_host` 时适配器计数为 0
5. `case5` 越界索引被拒（实测返回 6 = `HBA_STATUS_ERROR_ILLEGAL_INDEX`）
6. `case6` `OpenAdapterHandler("hba0")` 返回无效句柄 0
7. `case7` `FreeLibraryHandler() == HBA_STATUS_OK`
8. `case8/case8b` **[OHOS]** `dlopen("libhbalinux.so.2")` 成功且导出 `HBA_RegisterLibraryV2`
9. `case9` **[OHOS]** 无 fc_host sysfs 树时不虚报适配器
10. `case10` v1 注册入口 `HBA_RegisterLibrary()` 仍可用

## 验证结果

```sh
conan create archives/l/libhbalinux/1.0.16 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=libhbalinux/1.0.16
# rc=0；消费者断言 11 passed / 0 failed / 0 skipped（含 3 条 OHOS 专属）
```
---

**编译结束**: 2026-09-22 01:48
**最终状态**: built
