# clxclient 3.9.0 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，扁平布局，无 configure 脚本）
- 编译日期: 2026-09-16
- 编译器: /data/service/hnp/bin/clang++（OHOS clang 15, aarch64-unknown-linux-ohos）
- 状态: built

## 编译步骤

纯 Makefile 项目，无 configure。源码根目录直接执行：

```bash
make -j1 \
  CXX=<conan profile 的 tools.build:compiler_executables.cpp> \
  PCONFCFL="-I. -DCLTHREADS_NO_PTHREAD_CANCEL \
            -I<libx11>/include -I<libxft>/include \
            -I<freetype>/include/freetype2 -I<clthreads>/include \
            -I<xorgproto>/include -I<fontconfig>/include -I<libxrender>/include" \
  LDFLAGS="-L<libx11>/lib -L<libxft>/lib -L<freetype>/lib -L<clthreads>/lib \
           -L<xorgproto>/lib -L<fontconfig>/lib -L<libxrender>/lib" \
  libclxclient.so.3.9.0

make install PREFIX=/ LIBDIR=lib DESTDIR=$package_folder
```

install 传参说明：Makefile 用 `$(SUFFIX)`（`uname -m` 推导）拼 `LIBDIR`，传参时固定
`LIBDIR=lib` 避免 aarch64 上产生 `libaarch64`；`PREFIX=/` + `$(DESTDIR)$(PREFIX)/$(LIBDIR)`
（补丁后）保证安装到 `$DESTDIR/lib` 与 `$DESTDIR/include`。

3.9.0 与 3.9.2 的关键差异：3.9.0 包为扁平布局（Makefile 在包根），3.9.2 为
`source/` 子目录布局；3.9.0 用 `freetype-config` 探测 FreeType，3.9.2 用
`pkgconf --cflags freetype2`。补丁对两者做同等移除处理。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Makefile 调用 `` `freetype-config --cflags` `` 与 `--libs` | OHOS 无 freetype-config，且头/库路径由 Conan 包提供 | 补丁移除该探测，配方用 `PCONFCFL=-I<freetype>/include/freetype2` 与 `LDFLAGS=-L<freetype>/lib` 注入 |
| 2 | Makefile 硬编码 `-I/usr/X11R6/include` 与 `-L/usr/X11R6/$(LIBDIR)` | 上游面向本地 X11 安装路径，可移植构建不安全 | 补丁移除硬编码路径，配方注入 7 个依赖的 `-I/-L` |
| 3 | 链接规则硬编码 `g++` | 交叉/可移植构建需由 Conan profile 控制编译器 | 补丁改为 `$(CXX)`，配方从 `tools.build:compiler_executables` 取值传入 |
| 4 | OHOS 无裸 `install` / `ldconfig` 命令，且 HMBS install shim 会让分级安装产物悬空 | OpenHarmony PATH 无 coreutils 的 install，ldconfig 不存在；走 shim 安装的主库文件在包内呈悬空链接，test_package 的 runtime 收集 resolve 失败 | 补丁改用 `mkdir -p` + `cp -f` 做分级安装（不再经由任何 install 程序），去掉 `ldconfig` |
| 5 | `make install` 无 DESTDIR 支持 | 原规则直接写 `$(PREFIX)/...`，无法分级安装 | 补丁改为 `$(DESTDIR)$(PREFIX)/...`（参照 3.9.2） |
| 6 | 缺少 SONAME 符号链接 | 上游只建 `libclxclient.so` 一个链接，运行时 loader 找不到 `libclxclient.so.3` | 补丁补全 `.so` → `.so.3` → `.so.3.9.0` 完整链接链 |

## 上游测试审计

- 包内容：`clxclient-3.9.0.tar.bz2`（30272 字节，sha256 见 conandata.yml）仅含
  AUTHORS、COPYING、INSTALL、Makefile、Makefile-osx、clxclient.h 与 14 个 `.cc`
  源码，扁平布局，无 test 目录、无 *test* 文件。
- Makefile 目标：仅 `all`（隐式 `libclxclient.so.3.9.0`）、`install`、`clean`，
  无 `check`/`test` 目标，`make check` 报 `No rule to make target 'check'`。
- 结论：上游确无测试，按 `no_tests` 处理。`test_package/MANIFEST.yml` 已写入
  `upstream_tests_exist: false` 与完整 `upstream_test_audit`，
  `test()` 每轮复发 `HMBS_UPSTREAM_TEST_RESULT(status=no_tests)` 标记。

## 依赖版本

- libx11/1.8.13（制品仓 ohpcd 已发布）
- libxft/2.3.8（同上）
- freetype/2.14.3（同上）
- clthreads/2.4.0（本仓库已有归档）
- xorgproto/2025.1（`<X11/Xos.h>` 提供方）
- fontconfig/2.18.3（Xft.h 传递引用 `<fontconfig/fontconfig.h>`）
- libxrender/0.9.12（Xft.h 传递引用 `<X11/extensions/Xrender.h>`）

## 验证结果

- 编译：`libclxclient.so.3.9.0` 生成成功，预期 ELF64/AArch64，SONAME=libclxclient.so.3
- 上游测试：无（见上节审计），如实声明为 `no_tests`
- 消费者测试（test_package）：链接 libclxclient 成功；X_resman 用 XrmParseCommand
  喂入命令行资源，geometry/title/getb 共 3 项往返校验通过（不依赖 X display），
  测试二进制自发 `HMBS_TEST_PACKAGE_RESULT(discovered=3)`，运行退出码 0
- 待 HMBS 真机预检回填实测数字后，manifest `test_results` 与 PR 正文通过率以
  预检日志为准

## 注意事项

- 库链接 `-lclthreads -lpthread -lXft -lX11`，运行时需 libXft.so/libX11.so（由依赖链提供，conanrun 环境注入）。
- clxclient.h 头文件 include 了 `<X11/Xlib.h>`、`<X11/Xft/Xft.h>`、`<clthreads.h>` 与 FreeType 头，
  下游消费者必须继承这些依赖的 include 路径 → requirements 全部 `transitive_headers=True`。
- conandata.yml sources.url 为官方源 https://kokkinizita.linuxaudio.org/linuxaudio/downloads/clxclient-3.9.0.tar.bz2
  （R39：官方源，sha256 与实测下载一致）。
- 本轮只完成未提交工作树，真机全部门禁通过前不创建 PR。

---

**编译结束**: 2026-09-16
**最终状态**: built
