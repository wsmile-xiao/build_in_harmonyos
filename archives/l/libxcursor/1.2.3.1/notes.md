# libXcursor 1.2.3.1（=上游 1.2.3 + R37 版本后缀）适配笔记

## 概述

X cursor 主题加载/渲染客户端库，提供光标主题遍历、Xcur 文件解析、
ARGB/animated 光标创建 API。产物 libXcursor.so.1（`-version-number 1:0:2`
→ 1.0.2），`XCURSOR_LIB_VERSION` 宏 = 10203。

## OHOS 适配要点

- **依赖**：libx11/6.4.0、libxrender/0.9.12、libxfixes/6.1.0、
  xorgproto/2025.1。configure 运行
  `PKG_CHECK_MODULES(XCURSOR, xrender >= 0.8.2 xfixes x11 fixesproto)`；
  xrenderproto/fixesproto 由 xorgproto 提供（纯头文件），libXcursor
  链接 `-lXrender -lXfixes -lX11`。
- **依赖轨道（重要陷阱）**：制品仓 libxrender/0.9.12 的 recipe 钉
  libx11/**1.8.13**，而 libxfixes/6.1.0 与 libxext/6.4.0 钉 libx11/**6.4.0**
  （cmd-pkgs 轨道，与已合并 libxi/libxscrnsaver 一致）。必须在 recipe 里
  `self.requires("libx11/6.4.0", force=True)`，让 libxfixes/libxext 命中
  已发布二进制（免重建），libxrender/0.9.12 则对 6.4.0 重新源码构建
  （其 relocatable-libtool-metadata linker view 支持）。**切勿改强制
  1.8.13**：该轨道 libX11.la 会引用 libxcb.la，而 libxcb/1.16 不带 .la，
  下游任何源码构建（如传递依赖 libxext/6.4.0）会报
  `is not a valid libtool archive` 失败。
- **构建系统**：autotools，复用 CI 实证的 libxrender/0.9.12 交叉编译模式：
  `PkgConfigDeps`+`AutotoolsDeps` 解决 `PKG_CHECK_MODULES`，build 目录私有
  relocatable linker view 提供 LDFLAGS，`configure-ohos`（umask 077→022）
  经 `/system/bin/sh` 以 `--host=aarch64-linux-ohos` 交叉模式运行，`make -j1`
  同样走 `/system/bin/sh`（`export SHELL/CONFIG_SHELL=/system/bin/sh`），
  `.pc` 相对化 + 移除 libXcursor.la。OHOS 下 **不** 跑 `make check`（上游
  libXcursor 测试套件在沙箱中不必要）。
- **works-check 陷阱（关键）**：OHOS worker 的 clang 不能 *运行* conftest
  二进制。configure 若以原生模式（`--build == --host`）运行，autoconf 会尝试
  执行 conftest 并报 `C compiler cannot create executables`。必须以
  `--host=aarch64-linux-ohos`（config.guess 给出
  `aarch64-unknown-linux-ohos`，build≠host）进入 cross_compiling=yes 分支，
  此时 conftest 只链接不运行，`checking whether the C compiler works... yes`。
  同批 CI 中 libxrender 交叉通过、libxcursor 原生失败的实测即此原因。
- **config.guess/config.sub 补丁（必须，来自 libxrender/0.9.12 移植）**：上游
  config.guess 不认识 HarmonyOS——它 fall through 到通用 Linux 分支去 *编译*
  dummy.c 探测（需在 TMPDIR 写文件），在 OHOS worker 沙箱下
  `config.guess[1700]: can't create .../dummy.c: Permission denied` →
  `cannot guess build type`。libxrender 通过两个 conandata 补丁解决：
  `0002-config.guess.patch` 在 NetBSD 分支前插入 HarmonyOS 分支
  （`uname -s` 为 HarmonyOS 时直接 `echo aarch64-unknown-linux-ohos; exit`，
  不再编译 dummy.c）；`0001-config.sub.patch` 把 `ohos*` 加进合法 OS 列表、
  `linux-ohos*` 加进 kernel-os 校验。本配方按 libxcursor 的 config.guess/sub
  版本（2022-01-09 / 2022-01-03）做了 hunk 适配，`build()` 在生成
  configure-ohos 前 `apply_conandata_patches`。无此补丁时即使交叉模式也过不了
  "cannot guess build type"。
- **版本**：`-version-number 1:0:2` → libXcursor.so.1.0.2。Conan
  `cpp_info.libs = ['Xcursor']` 匹配文件名（`libXcursor.so`）。
- **头文件**：`X11/Xcursor/Xcursor.h` 自包含，消费者直接 include 即可。
- **pkg-config**：xcursor.pc 的 `Name: Xcursor`。Conan pkg_config_name 设为
  `xcursor`。

## 测试

test_package 构建两个无需 X server 的可执行文件：

1. `libxcursor_api_surface` — 对 libXcursor.so.1 全部 61 个导出函数
   （Xcursor*）生成强制活重定位。
2. `libxcursor_version_contract` — 25 条 ABI 断言：版本宏（1/2/3 → 10203）、
   XcursorImage（7 个 CARD32 + 末尾 XcursorPixel* 指针，offsetof 断言）、
   XcursorImages/XcursorFile/XcursorCursors 布局，以及 10 个导出函数通过
   强类型函数指针赋值做的编译期签名契约（非 sizeof 空操作）。

## 参考

- 官网: https://gitlab.freedesktop.org/xorg/lib/libxcursor
- 源码: https://xorg.freedesktop.org/archive/individual/lib/libXcursor-1.2.3.tar.xz

---

## 1.2.3.1 版本说明（2026-09-08 增补）

**背景**：为 gtk 3.24.52 X11 后端适配发布 OHOS binary（R37 版本后缀）。制品仓
`libxcursor/1.2.3` 仅有 recipe、无 OHOS 预编译 binary，gtk X11 后端依赖它
（meson dependency xcursor，可选但启用）→ 发布 1.2.3.1 补齐。

**变更**：无源码/配方逻辑修改，仅版本号 1.2.3 → 1.2.3.1 并完成 OHOS aarch64
本地构建（autotools，config.sub patch 沿用 1.2.3；依赖 libx11/6.4.0、libxfixes、
xorgproto 均已发布）。

**构建验证**：
```bash
conan create archives/l/libxcursor/1.2.3.1 --version=1.2.3.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```
test_package 真实调用 libXcursor API（XcursorGetVersion 等，R34）。

**编译日期**: 2026-09-08
**最终状态**: built（本地 W3 验证通过）
