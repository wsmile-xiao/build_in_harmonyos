# libXi 1.8.3 适配记录

## 任务信息
- 目标库: libXi（X Input extension client library）
- 版本: 1.8.3
- 上游: https://gitlab.freedesktop.org/xorg/lib/libXi
- 任务: 平台任务 3716（分支 `feat/libxi-1.8.3`）
- 源码: `https://xorg.freedesktop.org/archive/individual/lib/libXi-1.8.3.tar.xz`
- sha256: `7ad60056f01af4f786cfe93b3a7707447711626fc8da2637bec71a90409babe5`

## 角色定位
libXi 是 **libXtst 1.2.5（任务 3717）的硬前置**：libXtst 的
`PKG_CHECK_MODULES(XTST, [x11 >= 1.6] [xext >= 1.0.99.4] xi ...)`
要求 `xi` pkg-config 模块和 XInput.h 头文件，均只能由 libXi 提供。
本 PR 必须先于 libXtst 提交。

## configure.ac 依赖
```
PKG_CHECK_MODULES(XI,      [xproto >= 7.0.13] [x11 >= 1.6] [xextproto >= 7.0.3]
                            [xext >= 1.0.99.1] [inputproto >= 2.3.99.1])
PKG_CHECK_MODULES(XFIXES,  [xfixes >= 5])   # 注释明确: CFLAGS only
```
- `libXi_la_LIBADD = $(XI_LIBS)` → 只链 `-lX11 -lXext`。
- XFIXES 仅用于编译期：XInput2.h `#include <X11/extensions/Xfixes.h>` 需要
  `PointerBarrier` typedef（XIBarrier.c 使用）。
- 版本号 `-version-number 6:1:0` → libXi.so.6 / libXi.so.6.1.0。
- 无上游测试套件；源码树无 tests/。

## 关键决策：不依赖 libxfixes/6.0.2
libXi 需要 `xfixes >= 5` 模块（仅编译期）+ Xfixes.h 头文件。但：
- libxfixes/6.0.2 已发布配方被 pin 在 **libx11/1.8.13（Track A）**，其
  libtool-shadow 机制硬性要求 libx11 包内存在 `libX11.la`。
- libx11/6.4.0（cmd-pkgs Track B）**不打包 .la 文件**，无法满足该机制。
- 若把 libxfixes 拉入本图，将与 libxext/6.4.0 → libx11/6.4.0 形成
  **同一个图中两个 libx11 版本**的冲突，无既有配方先例可解。

因此本配方用两种本地手段满足 configure 期需求，**不引入 libxfixes**：
1. `generate()` 写入一个 pkg-config 桩 `xfixes.pc`（Version: 6.0.2），
   使 `PKG_CHECK_MODULES(XFIXES, [xfixes >= 5])` 通过；
2. 把 libXfixes 6.0.x 的 `Xfixes.h`（仅消费 `PointerBarrier` typedef）
   vendor 到源码 include 树（`include/X11/extensions/`，libXi 的
   AM_CPPFLAGS 已含该目录）。该头文件只在构建期使用，**不会被安装**。

产物 libXi.so 不引用 libXfixes.so（readelf 验证口径见 G3）。

## 轨道一致性
本图全部落在 cmd-pkgs Track B：`libx11/6.4.0` + `libxext/6.4.0` +
`xorgproto/2025.1`，与已合并的 libxscrnsaver/1.2.5 配方一致。
这三个依赖均已发布到 ohpcd remote（含 OHOS armv8 binary），图闭合。

## Conan 配方
- 模板: libXext/6.4.0（AutotoolsToolchain + PkgConfigDeps + VirtualBuildEnv）。
- `exports_sources`: conandata.yml + patches/* + include/*（vendor 头）。
- OHOS 环境变量: SHELL/CONFIG_SHELL/CC=clang/CXX=clang++/LD=ld.lld/
  AR=llvm-ar/RANLIB/STRIP/NM + `XI_CFLAGS`/`XI_LIBS`（-lX11 -lXext）+
  `XFIXES_CFLAGS`/`XFIXES_LIBS`（空，未链接）。
- configure 参数: `--disable-docs --disable-specs --without-xmlto
  --without-fop --without-xsltproc` + shared/static 组合。
- 收尾: 移除 .la、xi.pc 改相对 prefix（`prefix=${pcfiledir}/../..`）。
- package_info: `pkg_config_name="xi"`，libs=["Xi"]，cpp_info.requires 完整。

## 版本说明
- libXi 1.8.3 的 XInput2.h 声明了 XI 2.4 手势 API（XIGrabPinchGestureBegin
  等），实现位于 XIPassiveGrab.c（本版本确实导出）。
- xorgproto/2025.1 的 XI2.h 声明 `XI_2_Major 2 / XI_2_Minor 4`，与
  libXi 1.8.3 兼容（向后兼容，未改动既有结构）。

---

**编译结束**: 2026-08-22 18:00
**最终状态**: built
