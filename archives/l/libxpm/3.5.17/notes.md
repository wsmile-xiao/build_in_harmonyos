# libXpm 3.5.17 适配笔记

## 概述

X PixMap（XPM）图像文件格式读写库，X.Org 图形栈的基础组件。产物
libXpm.so.4（`-version-number 4:11:0` → 4.11.0），`XpmVersion`=4、
`XpmRevision`=11、`XpmIncludeVersion`=30411。

## OHOS 适配要点

- **依赖**：libx11/6.4.0、xorgproto/2025.1。configure 运行
  `PKG_CHECK_MODULES(XPM, xproto x11)`；xproto 由 xorgproto 提供（纯头文件），
  libXpm 链接 `-lX11`（`libXpm_la_LIBADD = $(XPM_LIBS)`）。
- **依赖轨道（重要陷阱）**：与 libxcursor 相同——制品仓存在 cmd-pkgs 6.4.0
  与 1.8.13 两条平行轨道。必须 `self.requires("libx11/6.4.0", force=True)`
  对齐已合并的 libxi/libxcursor；强制 1.8.13 会踩到 libX11.la 引用 libxcb.la
  而 libxcb/1.16 不带 .la 的 `is not a valid libtool archive` 失败。
- **构建系统**：autotools，复用已合并 libxrender/0.9.12 的 OHOS 交叉编译模式
  （详见下文"works-check 陷阱"）。configure 运行
  `PKG_CHECK_MODULES(XPM, xproto x11)`，由 PkgConfigDeps + AutotoolsDeps 提供
  .pc 与 CFLAGS/LDFLAGS（worker 上 pkg-config 在 /data/service/hnp/bin）。
- **works-check 陷阱（关键）**：OHOS worker 上不能跑 `--build == --host` 的本机
  模式——autoconf 的 C 编译器 works-check 会尝试 *执行* conftest 二进制，被
  OHOS 沙箱拦下而报 `C compiler cannot create executables`。libxrender 的适配
  笔记明确记录："configure required the target --host=aarch64-linux-ohos to
  enter cross-compiling mode"。因此 configure 必须以
  `--host=aarch64-linux-ohos` 进入交叉编译（config.guess 返回 build=
  aarch64-unknown-linux-ohos ≠ host），works-check 只链接不运行即通过。
- **config.guess/config.sub 补丁（必须，来自 libxrender/0.9.12 移植）**：上游
  config.guess 不认识 HarmonyOS——它 fall through 到通用 Linux 分支去 *编译*
  dummy.c 探测（需在 TMPDIR 写文件），在 OHOS worker 沙箱下
  `config.guess[1700]: can't create .../dummy.c: Permission denied` →
  `cannot guess build type`。libxrender 通过两个 conandata 补丁解决：
  `0002-config.guess.patch` 在 NetBSD 分支前插入 HarmonyOS 分支
  （`uname -s` 为 HarmonyOS 时直接 `echo aarch64-unknown-linux-ohos; exit`，
  不再编译 dummy.c）；`0001-config.sub.patch` 把 `ohos*` 加进合法 OS 列表、
  `linux-ohos*` 加进 kernel-os 校验。本配方按本包 config.guess/sub 版本
  （2023-01-01 / 2023-01-21）做了 hunk 适配，`build()` 在生成 configure-ohos
  前 `apply_conandata_patches`。无此补丁时即使交叉模式也过不了
  "cannot guess build type"。
- **cxpm 工具不构成链接风险**：cxpm/Makefile.am 无 LDADD，但 cxpm.c 直接
  `#include` 内部 src/*.c（data.c/parse.c/RdFToI.c/hashtab.c/misc.c/Attrib.c/
  Image.c），且这些文件不调用 Xlib 函数，cxpm 只需链接 libc。sxpm 因
  `PKG_CHECK_MODULES(SXPM, ... xt ...)` 无 libXt 自动禁用。
- **链接器视图**：复用 libxrender 的 `_prepare_linker_view()`——把依赖的
  .a/.la/.so 复制进 build/linker-view，并把 .la 的 `libdir`/`dependency_libs`
  重写为本机路径、去掉缺失的 .la 引用（libx11/6.4.0 的 libX11.la 引用
  libxcb.la 而 libxcb/1.16 不带 .la），从根上避免 libtool 报 "is not a valid
  libtool archive"。configure 参数 `LDFLAGS=-L<linker-view>`。
- **版本**：`-version-number 4:11:0` → libXpm.so.4。Conan `cpp_info.libs =
  ['Xpm']` 匹配文件名（`libXpm.so`）。
- **头文件**：`X11/xpm.h` 包含 Xlib.h/Xutil.h/Xfuncproto.h，函数经
  `FUNC(name,type,args)` 宏展开为 `extern _X_EXPORT` 声明。
- **pkg-config**：xpm.pc 的 `Name: Xpm`。Conan pkg_config_name 设为 `xpm`。

## 测试

test_package 构建两个无需 X server 的可执行文件：

1. `libxpm_api_surface` — 对 libXpm.so.4 全部 34 个导出函数（Xpm*）生成强制
   活重定位。
2. `libxpm_version_contract` — 版本宏（XpmIncludeVersion=30411）、
   XpmImage/XpmColor/XpmInfo/XpmExtension/XpmColorSymbol 布局（offsetof 断言，
   与指针宽度无关）、18 个导出函数强类型签名契约，以及 XPM 解析→写文件→读回
   →重新生成的完整 round-trip 冒烟测试（全路径不依赖 X server）。

- **XpmCreateDataFromXpmImage 单块内存契约（实测踩坑）**：该函数返回**一个**
  XpmMalloc 分配的连续块，行指针全部指向块内部（CrDatFrI.c 中
  `data = (char**)XpmMalloc(data_size)`，随后 `*(sptr+1) = *sptr +
  strlen(*sptr2) + 1` 链式指向块内）。调用方只需 `XpmFree(data_return)` 一次；
  逐行 `XpmFree(data_return[i])` 会二次释放块内指针，在 Bionic/scudo
  分配器下 SIGTRAP（Signal 5）崩溃。OHOS CI 的 round-trip 实测触发，对照
  man XpmCreateData："a single block malloc'ed data... free the data, using
  XpmFree when finished"——这是文档化契约，不是 libXpm 缺陷。
