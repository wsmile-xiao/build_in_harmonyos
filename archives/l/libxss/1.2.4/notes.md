# libxss (libXScrnSaver) 1.2.4 适配记录

## 任务信息
- 目标库: libxss (libXScrnSaver)
- 上游项目: https://gitlab.freedesktop.org/xorg/lib/libxscrnsaver
- 版本: 1.2.4
- 分支: feat/libxss-1.2.4
- 构建系统: autotools (configure.ac)

## W0 依赖检查
configure.ac 声明依赖: `x11 xext xextproto [scrnsaverproto >= 1.2]`

依赖检查结果 (conan download -r=ohpcd --only-recipe):
- `libx11/6.4.0`: recipe revision 63e25e48c3af73db324ce61d0dba9cce — 已发布
- `libxext/6.4.0`: recipe revision 20942ab436730e84acb01dcf565fda68 — 已发布
- `xorgproto/2025.1`: recipe revision f5274e33759da898a6e8d87d7708d47c — 已发布（提供 xextproto.pc 和 scrnsaverproto.pc）

构建工具检查:
- `util-macros/1.20.1`: recipe revision a0a83107876c0951e23b36cda8548324 — 已发布
- `automake/1.18`: recipe revision 65a7ba60030d238eb8bb32266391cfc5 — 已发布
- `libtool/2.5.4`: recipe revision fe9f8e735ad45469571cf4de3ce552f4 — 已发布

结论: 所有依赖和构建工具已在制品仓发布，依赖图闭合。

## 源码与构建系统分析
- 源码 URL: https://gitlab.freedesktop.org/xorg/lib/libxscrnsaver/-/archive/libXScrnSaver-1.2.4/libxscrnsaver-libXScrnSaver-1.2.4.tar.gz
- SHA256: e62636d3ce925f7411184b6d38c501676d0a7c83459bc477bf555f8c229cb85c
- 这是 GitLab archive tarball（非 release tarball），不含预生成 configure 脚本。
- 构建系统: autotools (configure.ac + Makefile.am + autogen.sh)
- configure.ac 使用 `AC_PROG_LIBTOOL`、`XORG_MACROS_VERSION(1.8)`、`AM_INIT_AUTOMAKE`
- 因此 build() 需先运行 `autoreconf -fi` 生成 configure 脚本。
- tool_requires: util-macros/1.20.1 (xorg-macros m4)、automake/1.18 (aclocal/automake)、libtool/2.5.4 (libtool m4 macros)

## Conan 配方策略
- 主配方使用 `AutotoolsToolchain` + `PkgConfigDeps` + `VirtualBuildEnv`。
- build_requirements 声明 util-macros/1.20.1、automake/1.18、libtool/2.5.4。
- VirtualBuildEnv 将 tool_requires 的 bin 目录注入 PATH，使 autoreconf 可执行。
- PkgConfigDeps 生成 libx11→x11.pc、libxext→xext.pc 映射。
- xorgproto 的 xextproto.pc 和 scrnsaverproto.pc 从 share/pkgconfig 复制到 generators 目录并重写 prefix。
- OHOS 构建时:
  - 注入 SHELL/CONFIG_SHELL 指向 /system/bin/sh 或 fallback。
  - 注入 CC/CXX/AR/RANLIB/STRIP/NM 工具路径（从 conf 或 PATH fallback）。
  - 注入 XSCRNSAVER_CFLAGS/XSCRNSAVER_LIBS 跳过 configure 的 pkg-config 查找。
  - 传递 --build/--host=aarch64-unknown-linux-gnu 跳过 config.guess。
  - 修补 configure 脚本的 umask 077→022 和 shebang。
- package 后清理 .la 文件并重写 .pc 的 prefix 为 ${pcfiledir}/../..

## test_package
test_package/test.c 不是空壳测试:
- 包含 `<X11/extensions/scrnsaver.h>`。
- 调用 `XScreenSaverAllocInfo()`，验证 `XScreenSaverInfo` 字段可写。
- 使用 `XFree()` 释放内存，覆盖 libXss 与 libX11 链接。
- 不连接 X server，不依赖 DISPLAY，适合真机/CI smoke。

## 产物
- lib/libXss.so (动态库)
- include/X11/extensions/scrnsaver.h
- lib/pkgconfig/xscrnsaver.pc
---

**编译结束**: 2026-08-29 14:48
**最终状态**: built

<!-- verified -->
