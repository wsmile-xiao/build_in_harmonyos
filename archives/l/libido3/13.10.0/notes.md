# libido3 13.10.0 适配笔记

## 版本与身份说明

- 上游：Ubuntu Ayatana "ido"（Indicator Display Objects），库产物 `libido3-0.1`。
- 无裸 13.10.0 tarball——13.10.0 是日历化 bzr 快照版本族（13.10.0+YY.MM.DD）。
- 官方映射（Scout-A 2026-09-26 核实）：Ubuntu 当前系列 0ubuntu4 源包 orig tarball
  `ido_13.10.0+22.10.20221007.orig.tar.gz`，
  sha256 `660b4feae9a6c8c7ba76251c3636c53c539cc2c287f9272fe2ec81d97a96c241`
  （与官方 dsc Checksums-Sha256 逐字比对一致）。
- recipe 版本字符串一律 13.10.0（configure.ac 内部自报 13.10.1 是上游 m4 遗留）。
- license：Ubuntu debian/copyright 声明双许可 LGPL-3 and/or LGPL-2.1；
  conanfile 取 `LGPL-2.1-or-later`。
- 构建系统：autotools；tarball 平铺无预生成 configure（autogen.sh 依赖
  gnome-common，仓内无）→ 配方内自举（见下）。

## W0b 历史经验核验（必做）

| # | 来源 | 结论 | 本轮处置 |
|---|------|------|----------|
| 1 | knowledge/graph E179.kv:16-23（ImportError: ELF 签名/Python 扩展） | rec_command: `--disable-introspection`（autotools） | 采纳：`--disable-introspection` + patch 0002 桩掉 GOBJECT_INTROSPECTION_CHECK（交叉编译 g-ir-scanner 需跑目标二进制） |
| 2 | knowledge/graph E216.kv（glib CMakeDeps 组件头传播失效） | 消费端走 pkg_check_modules + GLOB 兜底 | 采纳：test_package 走 pkg_check_modules(libido3-0.1 IMPORTED_TARGET)，.pc Requires 链传播传递头/库 |
| 3 | knowledge/graph E078.kv（musl BIND_NOW） | 解释型语言扩展模块 dlopen 符号解析面 | 本库无 Python/Perl 扩展模块；仅提示产物需完整 DT_NEEDED 闭包（链接闭包显式化落实） |
| 4 | knowledge/graph E090/E091（meson host_system） | meson 场景 | 本库 autotools，不适用 |
| 5 | 经验仓 main build-system/cairo-1.18.4.md | test_package `-I` 需绝对化 | 采纳：pkg_check_modules 输出绝对 -I（LIBIDO3_INCLUDE_DIRS） |
| 6 | 经验仓 main platform-detect/libnl3-3.12.0-config-guess-build-triple.md | config.guess 不识 OHOS → 显式三元组 | 采纳：`--build/--host=aarch64-unknown-linux-gnu`（ctpl/cdecl 同款） |
| 7 | build-chain-pitfalls.md:71-89（lld 链接闭包/libgee 案例） | 每依赖 libdir 显式 -L/-rpath-link；env 注入必须在 toolchain env 快照之前；libintl 绝对路径显式输入 | 采纳：generate() 内顺序落实（libgee 0.20.8.1 同款实现） |
| 8 | knowledge/graph E415.kv（CI mirror 原地改写 conandata.yml） | CI 后必须恢复 | CI 跑完以 `git status`/`git diff` 核验 conandata.yml 与 HEAD 逐字节一致（archive.ubuntu.com 非 github 域，预计不触发改写，仍核验） |
| 9 | abiword-plugin-docbook/3.0.8 conanfile（_run_autogen + tool automake/libtool） | HMDFS autoreconf 链 autoconf.m4f 冲突 → 直跑 aclocal/autoconf/autoheader/ltmain/automake | 采纳：`tool_requires(automake/1.18, libtool/2.5.4, pkgconf/3.0.5)` + `_bootstrap_autotools()` 同链 |
| 10 | libgee/0.20.8.1 conanfile（链接闭包 + dep .la 清理） | E236 stale .la（libdir='//lib'） | 采纳：build() 前清理依赖 lib/*.la，安装后清理自身 .la |

## 关键工程点

1. **ubuntu-private API 条件化（patch 0001）**：`src/idomenuitemfactory.c:21`
   无条件 `#include <gtk/ubuntu-private.h>`（Ubuntu 私有 GTK 头，vanilla GTK3
   无此文件）。Alpine `ubuntu-private.patch`（本地 tmp/ubuntu-private.patch）
   的解法是加 `--enable-ubuntu-private-api` 开关条件化整块；因 22.10 tarball
   的 `src/Makefile.am` 相对 17.04 去掉了 `-Werror`（其余四个文件逐字一致），
   补丁按 22.10 原始上下文重新生成（最小、可解释、可重复应用）。本配方
   `--disable-ubuntu-private-api`：`idomenuitemfactory.c` 成为空编译单元
   （GCC/clang 默认接受），`ido_init()` 退化为空操作，IdoMenuItemFactory
   扩展点不注册——test_package check2 以 dlsym 断言该符号缺失，守住这一
   OHOS 适配点不被回归。
2. **外部 m4 宏桩（patch 0002）**：tarball m4/ 只有 gcov.m4；
   `GOBJECT_INTROSPECTION_CHECK`/`CHECK_XORG_GTEST`/`GTK_DOC_CHECK` 三宏
   不可得。用 `m4_ifdef(..., [], [m4_define(...)])` 桩化（若真实宏存在则
   让位），同时保留 `--enable-introspection`/`--enable-gtk-doc` 选项合法，
   并定义 `HAVE_INTROSPECTION=false` 供 src/Makefile.am 的 automake 条件。
3. **NO_UPSTREAM_TESTS 证据（discovery 门禁）**：
   - 检查过的入口：
     a) `tests/Makefile.am`（tests/Makefile 生成物）——第 4 行注释
        "xorg-gtest isn't buildable https://bugs.launchpad.net/ubuntu/+source/xorg-gtest/+bug/1388892"，
        第 6 行 `check_PROGRAMS = `、第 7 行 `TESTS = `（均为空）；
        第 32-34 行 gtest-menuitems 的 TESTS/check_PROGRAMS 注册被注释，
        第 45-49 行显示其链接依赖 `-lX11 -lXi`（需 X display）。
     b) `configure.ac` —— `CHECK_XORG_GTEST`（第 137 行）为唯一测试框架
        入口，依赖 xorg-gtest（上游自己宣告不可构建）。
     c) `tests/gtest-menuitems.cpp` —— 4 个 TEST_F（依赖 X11/Xi 与 X
        display），非 OHOS 可验证面；不裁剪、原样保留在候选内（桩宏后
        该目录不构建任何程序）。
     d) Alpine 同族打包（ido）`options="!check"` 旁证。
   - 证据路径（tarball 内）：`tests/Makefile.am:4,6,7,32-34,45-49`、
     `configure.ac:134-137`、`tests/gtest-menuitems.cpp`。
   - 结论：`NO_UPSTREAM_TESTS`，discovery.status=EVIDENCE_COMPLETE；
     配方 `make check` 仍然执行并输出诚实的零用例
     `HMBS_UPSTREAM_TEST_RESULT`（status=no_upstream_tests, discovered=0）；
     真机验证面由 test_package 的 5 项消费者检查承担。
4. **链接闭包**：`generate()` 内先完成全部 `tc.extra_*`/`env` 注入再
   `tc.generate(env=env)`（快照前），每依赖 libdir 显式
   `-L/-Wl,-rpath/-Wl,-rpath-link`；glib `lib/libintl.so`（g_libintl_*
   唯一供给）以绝对路径进链接行；禁 `--allow-shlib-undefined`。验证：
   CI 日志中的真实链接行 + test_package 运行。
5. **产物后处理**：安装后清理 `.la`；`libido3-0.1.so.0` 用 libtool 真身
   拷贝为实体文件（HMDFS symlink 运行期不可靠，ayatana-ido 同款）；
   `_sign_installed_elfs()` 以 binary-sign-tool 自签（glib 配方同款）。
6. **on-device 自举链**（abiword-plugin-docbook 先例）：aclocal → autoconf
   → autoheader → ltmain.sh（$LIBTOOLIZE 包内复制）→ automake
   --add-missing；随后对生成 configure 打 E011 umask 补丁、注入 cp/mkdir
   install shim（E182/E188）、TMPDIR 重定向（E002）。

## 依赖图

与已发布的 `ayatana-ido/0.10.4-v2` 完全同闭包（同族后继、同 gtk/3.24.43 +
glib/2.84.0.1 图，含全部 RREV override），理由：该闭包是本机 CI 已验证的
gtk 图发布面；任何偏离（版本或 RREV）都会使 glib/gtk 偏离发布 identity 而
回退源码构建（ayatana-ido 配方注释第 15-17 轮实证）。

## 验证面

- 权威 CI：`ci/conan/build_and_test.sh`，`CI_BRANCH=feat/libido3-13.10.0`，
  profile `ci/conan/profiles/ohos-aarch64`（host 与 build 同 profile）。
- test_package：5 项检查（含 1 项 OHOS 特有适配断言 + 2 项无头 broadway
  widget 构造），输出 `HMBS_TEST_PACKAGE_RESULT`（discovered=5）。
