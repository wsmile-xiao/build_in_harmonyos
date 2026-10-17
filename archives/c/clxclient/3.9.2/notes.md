# clxclient 3.9.2 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，source/Makefile，无 configure 脚本）
- 编译日期: 2026-08-31
- 编译器: /data/service/hnp/bin/clang++（OHOS clang 15, aarch64-unknown-linux-ohos）
- 状态: built

## 编译步骤

纯 Makefile 项目，无 configure。在 `source/` 目录执行：

```bash
make -C source -j1 \
  CXX=<conan profile 的 tools.build:compiler_executables.cpp> \
  CXXFLAGS="-O2 -Wall -fPIC" \
  CPPFLAGS="-D_REENTRANT -D_POSIX_PTHREAD_SEMANTICS \
            -I<libx11>/include -I<libxft>/include \
            -I<freetype>/include/freetype2 -I<clthreads>/include" \
  LDFLAGS="-L<libx11>/lib -L<libxft>/lib -L<freetype>/lib -L<clthreads>/lib" \
  libclxclient.so.3.9.2

make -C source install PREFIX=/ LIBDIR=lib DESTDIR=$package_folder
```

install 传参说明：Makefile 用 `$(SUFFIX)`（`uname -m` 推导）拼 `LIBDIR`，传参时固定
`LIBDIR=lib` 避免 aarch64 上产生 `lib64`；`PREFIX=/` + `$(DESTDIR)$(PREFIX)/$(LIBDIR)`
（补丁后）保证安装到 `$DESTDIR/lib` 与 `$DESTDIR/include`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Makefile 硬编码 `CXXFLAGS += -march=native` | 上游为本地优化编写，交叉/可移植构建不安全 | 补丁移除该行，编译器与优化标志由 Conan profile / 配方控制 |
| 2 | Makefile `CPPFLAGS += $(shell pkgconf --cflags freetype2)` | OHOS 无 pkgconf，且 freetype 头路径由 Conan 包提供 | 补丁移除 pkgconf 调用，配方用 `-I<freetype>/include/freetype2` 注入 |
| 3 | OHOS 无裸 `install` / `ldconfig` 命令 | OpenHarmony PATH 无 coreutils 的 install，ldconfig 不存在 | 补丁引入 `INSTALL ?= /bin/install`（toybox），去掉 `ldconfig` |
| 4 | `make install` 安装路径拼接 | `$(DESTDIR)$(LIBDIR)` 在 `LIBDIR=lib` 时拼成 `...plib` | 补丁改为 `$(DESTDIR)$(PREFIX)/$(LIBDIR)`（参照 zita-alsa-pcmi/clthreads） |
| 5 | 缺少 SONAME 符号链接 | 上游只建 `libclxclient.so` 一个链接，运行时 loader 找不到 `libclxclient.so.3` | 补丁补全 `.so` → `.so.3` → `.so.3.9.2` 完整链接链（rm -f + ln -s） |

## 依赖版本

- libx11/1.8.13（制品仓 ohpcd 已发布，`conan download --only-recipe` 已验证）
- libxft/2.3.8（同上）
- freetype/2.14.3（同上）
- clthreads/2.4.0（同上，本仓库已有归档）

## 验证结果

- 编译：libclxclient.so.3.9.2 生成成功，ELF64/AArch64，SONAME=libclxclient.so.3
- 上游测试：无（`make -C source check` → "No rule to make target 'check'"），已如实声明
- 消费者测试（test_package）：链接 libclxclient 成功；X_resman 用 XrmParseCommand
  喂入命令行资源，get/getb 往返校验通过（不依赖 X display），运行退出码 0
- `conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=...` 本地验证通过

## 注意事项

- 库链接 `-lXft -lX11 -lpthread`，运行时需 libXft.so/libX11.so（由依赖链提供，conanrun 环境注入）。
- clxclient.h 头文件 include 了 `<X11/Xlib.h>`、`<X11/Xft/Xft.h>`、`<clthreads.h>` 与 FreeType 头，
  下游消费者必须继承这些依赖的 include 路径 → requirements 全部 `transitive_headers=True`。
- conandata.yml sources.url 为官方源 https://kokkinizita.linuxaudio.org/linuxaudio/downloads/clxclient-3.9.2.tar.bz2
  （R39：官方源，sha256 与本地实测一致，HTTP 200 可达）。

---

**编译结束**: 2026-08-31
**最终状态**: built
