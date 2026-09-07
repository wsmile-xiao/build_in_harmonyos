# libcanberra 0.30 适配笔记

## 概述

XDG Sound Theme/Name 事件声音库（公共 API 为 `canberra.h` /
`libcanberra.so.0`）。上游 `-version-info 2:5:2` → `libcanberra.so.0`
（真实文件 `libcanberra.so.0.30.5`）。本次做最小自包含配置编译并发布共享库，
外加两个真实 consumer 测试在 **built-in null 驱动**上驱动公共 API——
null 驱动无需任何音频设备，可在 OHOS CI 上真实执行。

## OHOS 适配要点

- **vorbis 强制依赖绕过（关键）**：上游 `configure.ac:586`
  `PKG_CHECK_MODULES(VORBIS, [vorbisfile])` 是**无条件**的，没有 `--disable-*`
  开关——缺 libvorbisfile 时库存 configure 直接中止。OHPCD 制品仓没有
  vorbis/libogg。生成的 configure 内置的是老版 pkg.m4：**只有当
  `VORBIS_CFLAGS` 与 `VORBIS_LIBS` 同时非空**才走 env 分支、永不调用
  pkg-config。配方喂 `VORBIS_CFLAGS=-DHAVE_VORBIS=0`、`VORBIS_LIBS=' '`
  （注意有一个空格）。`HAVE_VORBIS` **没有**任何 `AC_DEFINE`
  （config.h.in 里也没有），不会与 `-DHAVE_VORBIS=0` 冲突；该 `-D` 经
  `libcanberra_la_CFLAGS = $(AM_CFLAGS) $(VORBIS_CFLAGS)` 到达每个编译单元，
  `#if HAVE_VORBIS` 即求值为 0。若将来 vorbis/libogg 入库，改
  `-DHAVE_VORBIS=1` 并补 conan requirements 即可原样恢复 .ogg 解码路径：
  - `patches/0001` 把整份 read-vorbis.c（唯一 `#include
    <vorbis/vorbisfile.h>` 的文件）实现包进 `#if HAVE_VORBIS ... #endif`；
  - `patches/0002` 把 read-sound-file.c 里 vorbis fallback（open 重试、
    close、channel map、s16 读取、size）分别包进守卫，WAV（read-wav.c）
    保留。
- **驱动选择 `--with-builtin=null`**：pulse/alsa/gstreamer/... 驱动是
  libltdl 可加载模块，需要 libltdl + 运行时插件目录，两者在 OHOS 都不适用。
  `--with-builtin=null` 恰好把一个驱动（null.c）编进 libcanberra.so 并关闭
  BUILTIN_DSO——不编 dso.c/driver-order.c，也不链 `$(LIBLTDL)`。null 驱动的
  `driver_play()` 同步报告完成，正适合无头冒烟。
- **null.c 缺 `driver_playing()`（上游疏漏）**：null.c 只实现了
  driver_open/destroy/change_device/change_props/play/cancel/cache 七个函数，
  但 common.c:717 无条件调用 `driver_playing()`（模块模式下由 DSO 包装器补上）。
  `patches/0003` 补 `*playing = 0` 的 stub，否则共享库链接不过。
- **只构建 `src` 子目录**：顶层 Makefile.am `SUBDIRS = src gtkdoc doc`；
  gtkdoc/ 需要 gtk-doc 工具链、doc/ 是生成文档，都不需要。配方只
  `make -C src` / `make -C src install DESTDIR=...`，libcanberra.pc 是顶层
  AC_CONFIG_FILES 产物，由配方自行复制进 package `lib/pkgconfig/` 并把
  `prefix=` 改写为 `${pcfiledir}/../..`、删除 `libcanberra.la`。
- **configure 模式（CI 教训 build #40768）**：沿用 libxrender/0.9.12 模式，
  configure 在 `/system/bin/sh` 下以 `--host=aarch64-linux-ohos --srcdir=...`
  运行，只给 `--host` 不给 `--build`。libcanberra 0.30（2009）自带的
  `config.guess`/`config.sub` 太老：CI 上 `uname -s = HarmonyOS` 令 config.guess
  无从猜 build → `error: cannot guess build type; you must specify one`；
  且 config.sub 连 `aarch64-linux-ohos` 都拒（`system ohos not recognized`）。
  修复 = 仿 libxrender 的两个补丁（本地已验：`bash config.sub
  aarch64-linux-ohos` → `aarch64-unknown-linux-ohos`；假 uname=HarmonyOS 跑
  config.guess → `aarch64-unknown-linux-ohos`）：
  - `patches/0004` 给 config.guess 加 HarmonyOS 预分支 → 输出
    `aarch64-unknown-linux-ohos`；
  - `patches/0005` 让 config.sub 接受 `linux-ohos*`（KERNEL-OS 解析表 +
    认可表各一处）。
  - **libltdl 硬门禁（CI 教训 build #40797，`patches/0006`）**：configure 在
    AC_DEFUN ltdl 探测后 `if test "x$LIBLTDL" = "x"; then AC_MSG_ERROR(Unable
    to find libltdl.)`——**无条件**硬错（configure.ac:115-175 没有
    `--disable-ltdl` 之类开关）。但 src/Makefile.am 只在 `if BUILTIN_DSO`
    分支里链 `$(LIBLTDL)`；`--with-builtin=null` 已关 BUILTIN_DSO，因此把
    该 `as_fn_error` 中和为 `LIBLTDL=`（空赋值）完全安全——LIBLTDL 保持空，
    不编 dso.c 也不需要 ltdl。这行改造必须在 configure.ac 里做的话无法动态
    注入，故直接打生成的 configure（`patches/0006`，dry-run 对纯净 configure
    干净应用）。若将来改为模块驱动（--with-builtin=pulse 等）需还原此补丁。
  配置自适应：configure 先链接并试跑一个 conftest，能跑→native
  （cross_compiling=no），被拦→`cross_compiling=yes` 走 cross fallback
  （AC_C_BIGENDIAN 等不再试跑二进制），都不硬错。生成的 configure 里把
  `umask 077`（全文恰好两处）改写为 `umask 022`。
- **导出面**：18 个公共函数（5 个 ca_proplist_*：create/destroy/sets/setf/set
  + 13 个 ca_context_*：create/set_driver/change_device/open/destroy/
  change_props/change_props_full/play_full/play/cache_full/cache/cancel/playing）
  + `ca_strerror`。`CA_SUCCESS == 0`，`CA_ERROR_*` -1..-18，
  `_CA_ERROR_MAX == -19`（哨兵，`ca_strerror` 对 -19 与正数都返回 NULL）。
  版本宏 `CA_MAJOR (0)` / `CA_MINOR (30)` / `CA_CHECK_VERSION(major,minor)`。

## 测试

test_package 构建两个 executable（均链接 `libcanberra::libcanberra`，`-Werror`），
在 built-in null 驱动上运行（无音频设备）：

1. `libcanberra_api_surface` — 对 19 个导出符号各取强类型函数指针（载入期
   活重定位），扫 -18..0 全部错误码的非空描述，验证 `ca_strerror(1000) == NULL`，
   proplist create/destroy 冒烟。
2. `libcanberra_version_contract` — 编译期契约 `#if CA_MAJOR != 0` /
   `CA_MINOR != 30`（版本号是 #define 宏，预处理可见）+ **错误码数值在
   运行时 `CHECK()` 锁定**（`CA_ERROR_*` 是 enum 常量，预处理不可见——若
   用 `#if CA_ERROR_X != -N` 测，未定义标识符按 0 求值，19 个负值断言全
   炸，CI build #40805 实测；改运行时 CHECK 即过）+ CA_CHECK_VERSION 宏语义 +
   ca_strerror 字符串表 + null 驱动完整生命周期：create → set_driver("null")
   → change_device → change_props_full → open → play_full（同步回调断言
   CA_SUCCESS/正确 id/userdata）→ playing==0 → cancel → cache_full 返回
   CA_ERROR_NOTSUPPORTED → destroy；外加失败模式：set_driver("bogus") 后
   open 返回 CA_ERROR_NODRIVER、open 后 set_driver 返回 CA_ERROR_STATE、
   无 event.id 的 play/cache 返回 CA_ERROR_INVALID、varargs play/change_props
   （NULL 哨兵）正常。OHOS 下先经 binary-sign-tool 签名（.codesign 校验）再执行。

> 上游 libcanberra 0.30 **没有自动化测试**：无 check_PROGRAMS/TESTS；唯一可执行
> test-canberra 是 noinst 演示程序（无断言，需真实音频后端播放系统声音文件）。
> 两个 consumer 测试即"上游无测试、适配后补全"的覆盖（详见 PR body）。
