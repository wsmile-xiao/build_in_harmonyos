# yp-tools 4.2.3 适配笔记

## 编译环境
- 构建系统: autotools（tag archive **不含 configure**，需 autogen.sh 自举）
- 编译日期: 2026-09-22
- 编译器: clang 15.0.4（OHOS SDK，默认 target `aarch64-unknown-linux-ohos`）
- 状态: built（本地 conan create 通过）
- 目标包: application（CLI 工具集，无库产物）

## 编译步骤

```sh
# 1) bootstrap（生成 configure；tool_requires 提供 automake/libtool/autoconf/gettext-autopoint）
PATH="<autoconf>/bin:<m4>/bin:$PATH" PERL=perl \
  PERL5LIB="<automake>/share/automake-1.18:<autoconf>/share/autoconf" \
  NOCONFIGURE=1 sh ./autogen.sh

# 2) configure（--build 显式给出，config.guess 不识别 HarmonyOS）
./configure --prefix=<prefix> --build=aarch64-unknown-linux-ohos
#   环境: CPPFLAGS=-I<gettext>/include -I<libxcrypt>/include
#         LDFLAGS =-L<gettext>/lib -L<libxcrypt>/lib
#         LIBS    =<gettext>/lib/libintl.a   （静态链接 libintl）

# 3) 构建 + 上游测试 + 安装
make -j1
make check          # 上游测试入口（patch 0002 注册 TESTS=xdrfile-test）
make install DESTDIR=<staging>
```

## 遇到的问题与解决方案

| # | 问题（首个真实错误） | 根因 | 解决方案 |
|---|--------------------|------|---------|
| 1 | `autogen.sh`：`Can't load .../perl5/5.42.2/.../Cwd.so for module Cwd: Error relocating Cwd.so: Perl_my_cxt_init: symbol not found` | conan perl/5.42.2 的 XS 模块（Cwd.so/IO.so）被 SDK perl（shebang `/data/service/hnp/bin/perl` 5.42.0）加载；VirtualBuildEnv 注入的 PERL5LIB 指向另一套 perl 的模块树 → XS ABI 失配 | build() 中把 `PERL5LIB` 收敛为工具包的纯 Perl 模块目录（`automake/share/automake-1.18`、`autoconf/share/autoconf`），核心 XS 模块回落到解释器自带 @INC（知识库 DRAFT-6049 同因同解） |
| 2 | `nicknames.c:102: error: incompatible integer to pointer conversion passing 'int' to parameter of type 'const char *'`（`gettext()` 隐式声明） | OHOS sysroot 的 `libintl.h` 只有宏、**无函数原型**；`ENABLE_NLS` 未生效时 libintl 未被发现 | configure 阶段提供 `-I<gettext>/include`（真实 libintl.h）与 `-L<gettext>/lib`，使 `AC_CHECK_LIB` 命中 gettext → `ENABLE_NLS=1` |
| 3 | `ld.lld: error: undefined symbol: libintl_gettext`（链接 ypwhich） | 上游 `src/Makefile.am` 的 `LDADD` 未引用 `@INTLLIBS@`（其假设 gettext 在 libc 内，glibc 成立、musl 不成立）；且 sysroot 无 libintl 库 | 在 `LIBS` 中直接静态链接 `<gettext>/lib/libintl.a`：CLI 工具自包含（运行时 NEEDED 仅 `libc.so`），避免依赖 LD_LIBRARY_PATH |
| 4 | `yppasswd.c:718: error: incompatible integer to pointer conversion assigning to 'char *' from 'int'`（`getpass()` 隐式声明） | OHOS musl 既不在 `<unistd.h>` 声明 `getpass()`，共享 `libc.so` 也不导出该符号（仅静态 `libc.a` 有） | patch 0001 `AC_CHECK_FUNCS([getpass])` + patch 0005 自备 `getpass()` 实现（termios 关回声读 /dev/tty），`HAVE_GETPASS` 探测为真时仍走 libc |
| 5 | `yppasswd.c:718` 后续 `ld.lld: error: undefined symbol: getpass` | 同上（musl 共享 libc 无该符号） | 同 4，`getpass` 由本包提供（实测 yppasswd 内 `T getpass`） |
| 6 | `configure: error: cannot guess build type`（`config.guess` 不识别 HarmonyOS，且 HMDFS 上临时目录权限导致创建 dummy.c 失败） | automake 1.18 附带的 config.guess（2024-07-27）无 HarmonyOS 分支，`uname -s=HarmonyOS` 无法识别 | configure 显式 `--build=aarch64-unknown-linux-ohos`（该三元组 config.sub 支持：`config.sub aarch64-linux-ohos → aarch64-unknown-linux-ohos`）；与仓内 libtirpc/1.3.7 配方同一做法 |
| 7 | `make install` → `ln: cannot create hard link from ... to .../ypchsh: Operation not permitted` | HMDFS 不支持硬链接（`link(2)` 返回 EPERM；实测同目录 `ln -f` 失败、`ln -s` 成功） | patch 0004 把 `install-exec-hook` 的 `ln -f` 改为 `rm -f && ln -s`（别名软链） |

## 源码修改（patches/）

| 补丁 | 文件 | 内容 |
|------|------|------|
| 0001-configure.ac.patch | `configure.ac` | 新增 `AC_CHECK_FUNCS([getpass])`（探测 getpass 是否可链接） |
| 0002-lib-Makefile.am.patch | `lib/Makefile.am` | 新增 `TESTS = xdrfile-test`，使上游测试真正被 `make check` 执行（上游只声明了 `check_PROGRAMS`） |
| 0003-lib-xdrfile-test.c.patch | `lib/xdrfile-test.c` | 无 ypbind3 绑定时打印 SKIP 并 `return 77`（automake 跳过约定），替代对 NULL 解引用；并支持可选主机参数（默认仍是上游的 `phex`） |
| 0004-src-Makefile.am.patch | `src/Makefile.am` | `install-exec-hook` 的别名安装由硬链接改为符号链接（HMDFS 限制） |
| 0005-src-yppasswd.c.patch | `src/yppasswd.c` | `#ifndef HAVE_GETPASS` 时提供 `getpass()` 实现（termios，读 /dev/tty） |

**补丁裁剪（重要）**：`refresh-patch --auto` 首次生成 11 个补丁，其中 6 个（`INSTALL`、`install-sh`、`m4/libtool.m4`、`m4/ltoptions.m4`、`m4/ltversion.m4`、`mkinstalldirs`）是 **autogen.sh / `libtoolize --copy` / `automake --add-missing --copy` 覆盖过的生成物**，不是源码修改，已删除；仅保留 5 个真实源码补丁。所有补丁在原始 tarball 上 `patch -p1 --dry-run` 全部通过。

## 依赖版本

| 类型 | 包 | 版本 | 说明 |
|------|----|------|------|
| requires | libnsl | 2.0.1 | 提供 `rpcsvc/yp_prot.h`、`ypclnt.h`、`yppasswd.h` + `libnsl.a`（静态）；自身 `requires libtirpc/1.3.Z` |
| requires | libtirpc | 1.3.7 | 提供 `rpc/*.h`（`-I.../include/tirpc`）+ `libtirpc.a`（静态） |
| requires | gettext | 0.22.5.1 | `include/libintl.h` + `lib/libintl.a`（静态链接）；同时作为 tool_requires 提供 `autopoint/msgfmt/xgettext` |
| requires | libxcrypt | 4.5.2 | `include/crypt.h`（有原型）+ `lib/libcrypt.a`（静态）；sysroot 的 `crypt.h` 无原型、`libcrypt.a` 为 8 字节空桩 |
| tool_requires | automake | 1.18 | `aclocal`/`automake`（bootstrap） |
| tool_requires | libtool | 2.5.4 | `libtoolize`（`LT_INIT`） |
| tool_requires | autoconf / m4 | 2.72 / 1.4.19 | `autoreconf`/`autoheader`/`m4` |
| tool_requires | pkgconf | 3.0.6 | `PKG_CHECK_MODULES` 探测 libnsl/libtirpc |
| tool_requires | gettext | 0.22.5.1 | `autopoint`（`AM_GNU_GETTEXT([external])` 自举） |

## 验证结果

```bash
$ make check
SKIP: xdrfile-test
# TOTAL: 1  # PASS: 0  # SKIP: 1  # FAIL: 0  # ERROR: 0
xdrfile-test: SKIP: no ypbind3 binding for host 'phex'
SKIP xdrfile-test（退出码 77，automake 约定为 SKIP）      # make check 整体 rc=0

$ ./src/yptest        # 上游内建 9 用例，全部被执行到（无 NIS 服务器 → 报错，rc=6）
Test 1: domainname ... Test 9: yp_all

$ test_package/test_yp_tools.sh <pkg>
== SUMMARY: PASS=44 FAIL=0 SKIP=0 (total=44) ==    # rc=0
```

上游 `make check` 的 SKIP 属**环境性跳过**（不是失败）：上游测试硬编码主机 `phex` 不可解析，且 OHOS 无 `/etc/netconfig` 且 `/etc` 只读 → libtirpc 的 `netdir_*` 无法初始化（实测即使换成可解析主机 `localhost`、设置 `NETPATH=udp` 亦同）。
NIS 服务器相关用例（ypcat/ypmatch/ypwhich/yppoll/ypset/yptest）在无 ypbind/服务器的环境下按预期报错，属"被执行到但环境不可用"，已在 test_package 中固化为可重复断言。

## 对话记录

### 对话 #1 [2026-09-22] init-build 与源码核验

- 操作: `python3 scripts/ohc-run.py init-build yp-tools 4.2.3 --url=https://github.com/thkukuk/yp-tools/archive/refs/tags/v4.2.3.tar.gz --auto`
- 结果: rc=0；源码 `yp-tools-4.2.3.work`（115 条目，sha256 `62b2278d…`）；`lang-preflight` rc=0（detected=c）
- 发现: 上游 tag archive **不含 configure**（`.gitignore` 忽略 `/configure`），仅 `configure.ac` + `autogen.sh`

### 对话 #2 [2026-09-22] bootstrap 首个真实错误（conan perl 与 SDK perl ABI 失配）

- 问题: `sh ./autogen.sh` 报 `Can't load .../perl5/5.42.2/.../Cwd.so for module Cwd: Error relocating Cwd.so: Perl_my_cxt_init: symbol not found`
- 根因: conan perl/5.42.2 的 XS 模块被 SDK perl（automake/aclocal 的 shebang 指向 `/data/service/hnp/bin/perl`，5.42.0）加载，而 VirtualBuildEnv 注入的 PERL5LIB 指向另一套 perl 的模块树
- 操作: `PERL=perl PERL5LIB="<automake>/share/automake-1.18:<autoconf>/share/autoconf"` 后重跑 autogen.sh
- 结果: rc=0，`configure` 生成成功（仅剩 obsolete 宏告警）

### 对话 #3 [2026-09-22] 编译/链接三个真实错误（musl 桩头文件与缺失符号）

- 问题 1: `nicknames.c:102: error: incompatible integer to pointer conversion …`（`gettext()` 隐式声明）→ sysroot `libintl.h` 无函数原型
- 修复 1: 提供 `-I<gettext>/include -L<gettext>/lib`，使 libintl 被探测到、`ENABLE_NLS=1`
- 问题 2: `ld.lld: error: undefined symbol: libintl_gettext` → 上游 `LDADD` 未引用 `@INTLLIBS@`（假设 gettext 在 glibc 内）
- 修复 2: `LIBS=<gettext>/lib/libintl.a` 静态链接
- 问题 3: `yppasswd.c:718: error: … getpass`，随后 `ld.lld: error: undefined symbol: getpass` → musl 既不声明也不导出 `getpass`（仅静态 `libc.a` 有）
- 修复 3: patch 0001（`AC_CHECK_FUNCS([getpass])`）+ patch 0005（自备 termios 实现）
- 结果: `make -j1` rc=0，9 个可执行文件生成；`readelf -d` 显示 NEEDED 仅 `libc.so`

### 对话 #4 [2026-09-22] 安装、上游测试与 conan 全链路

- 问题: `make install` 在 `install-exec-hook` 报 `ln: cannot create hard link …: Operation not permitted`（HMDFS 不支持 `link(2)`），需移除对硬链接的依赖
- 操作: patch 0004（别名改 `rm -f && ln -s`）；同时 patch 0002/0003 让 `make check` 真正执行上游测试并支持 SKIP（77）
- 结果: `make install DESTDIR=…` rc=0（13 个可执行项 + 4 个软链别名 + locale/man/nicknames）；`make check` rc=0（`SKIP: xdrfile-test`）；`conan create` rc=0；`conan-verify` G0-G4 全 PASS；W3 本地 CI 模拟通过；test_package 44/44 PASS

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/` | 13 个可执行项：ypwhich、ypmatch、ypcat、yppasswd、yppoll、ypset、yp_dump_binding、yptest、domainname + 别名 ypchsh/ypchfn/ypdomainname/nisdomainname（软链）。Conan 以 `--prefix=/` 生成 Makefile 参数并把 `sbindir` 映射到同一 `bin/`（`--sbindir=${prefix}/bin`），因此上游的 sbin 工具也落在包内 `bin/` |
| `share/locale/{de,sv}/LC_MESSAGES/yp-tools.mo` | NLS 翻译数据（de 14 KB） |
| `share/man/{man1,man5,man8}` | 13 个 man 页 |
| `var/yp/nicknames` | 上游数据文件（map 别名表，按上游安装布局保留） |
| `licenses/COPYING` | GPL-2.0 许可证文本 |

## 注意事项

- 运行时 `ypcat/ypmatch/ypwhich/yppoll/ypset/yptest` 需要可达的 ypbind/NIS 服务器，并且 libtirpc 需要 `/etc/netconfig`（OHOS 上 `/etc` 只读，通常缺失）；本包只保证"客户端工具可执行 + 优雅报错"。
- 4 个别名是**符号链接**（HMDFS 不支持硬链接）；打包/解包工具需保留软链语义。
- 所有第三方依赖均静态链接（libnsl/libtirpc/libxcrypt/libintl），产物仅依赖 musl `libc.so`（便于离线部署）。
- **NLS 位置注意**：Conan 以 `--prefix=/` 配置，编译进二进制的 `LOCALEDIR` 为 `//share/locale`；`.mo` 数据随包安装在 `<pkg>/share/locale`。因此只有在把包内数据安装到系统根（`/share/locale`）时才会出现翻译输出，直接从 conan 缓存运行则回退为英文 msgid（功能不受影响）。这是 Conan autotools 包"可重定位布局 + prefix=/"的通用取舍，未额外把 conan 缓存绝对路径烧入二进制。
---

**编译结束**: 2026-09-22 02:34
**最终状态**: built
