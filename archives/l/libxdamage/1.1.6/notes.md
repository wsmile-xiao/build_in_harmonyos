# libXdamage 1.1.6 — HarmonyOS PC 适配笔记

## 上游信息

- 上游版本: libXdamage 1.1.6（最新稳定版）
- 上游仓库: https://gitlab.freedesktop.org/xorg/lib/libxdamage
- soname: `-version-number 1:1:0` → `libXdamage.so.1.1.0`

## 依赖分析

`configure.ac`:
```
DAMAGEEXT_VERSION=`echo $VERSION | sed 's/^\([0-9][0-9]*\.[0-9][0-9]*\).*$/\1/'`  # 1.1
PKG_CHECK_MODULES(XDAMAGE, [damageproto >= $DAMAGEEXT_VERSION xfixes fixesproto xextproto x11 xproto >= 7.0.22])
```

- `x11` / `xfixes`: 链接级依赖，`libXdamage_la_LIBADD = $(XDAMAGE_LIBS)` = -lXfixes -lX11
- `damageproto` / `fixesproto` / `xextproto` / `xproto`: 头文件级依赖，xorgproto/2025.1 提供
- 全部在 cmd-pkgs 同轨（libx11/6.4.0 + libxext/6.4.0 + libxfixes/6.1.0 + xorgproto/2025.1）

## 适配要点

- 复用 CI 已验证的 OHOS autotools 工具链模式（libxcb/libxi/libxcomposite）
- `generate()`: XDAMAGE_CFLAGS（依赖 include 目录）、XDAMAGE_LIBS="-lXfixes -lX11"
- Xdamage.h include <X11/extensions/Xfixes.h>（XserverRegion 用于 Subtract/Add）
- 头文件级依赖 xorgproto 用 `transitive_headers=True` 消费（知识 E340）
- 导出符号（6 个）: XDamageQueryExtension / XDamageQueryVersion / XDamageCreate /
  XDamageDestroy / XDamageSubtract / XDamageAdd
- ABI 类型: `Damage`(=XID)、`XDamageNotifyEvent`、XserverRegion(来自 Xfixes)

## OHOS works-check 陷阱 + config 补丁（关键）

- **works-check 陷阱（实证）**：libxdamage 1.1.6 最初与本机模式 configure
  （`--build == --host == aarch64-unknown-linux-gnu`）构建，7 次 CI 全部在
  configure 期失败：`C compiler cannot create executables`。根因是 autoconf 的
  works-check 会尝试执行 conftest 二进制，被 OHOS 沙箱拦截（worker 相关、
  非确定——同构 libxcomposite 曾侥幸通过）。修复：`generate()` 里
  `tc.update_configure_args` 强制
  `--build=aarch64-unknown-linux-ohos --host=aarch64-linux-ohos`，raw triplet
  不同 → 进入交叉模式，works-check 仅链接不运行即通过。
- **config.guess/config.sub 补丁（必须）**：config.sub（2021-08-14）不认识
  ohos，需加 `ohos*`（合法 OS）+ `linux-ohos*`（kernel-os）；config.guess
  （2021-06-03）不认识 HarmonyOS，fall through 到编译 dummy.c 探测
  （`can't create .../dummy.c: Permission denied`），需在 NetBSD 分支前插入
  HarmonyOS 分支直接 `echo aarch64-unknown-linux-ohos; exit`。conandata 挂
  `0001-config.sub.patch` / `0002-config.guess.patch`，`build()` 在 configure
  前 `apply_conandata_patches`。补丁由 libxrender/0.9.12 移植、按版本 hunk
  适配（本包 2021-06-03 / 2021-08-14 与 libxpm 的 2023-01-01 / 2023-01-21
  不同）。

## 测试

- `libxdamage_api_surface`: 6 个导出符号强类型重定位
- `libxdamage_version_contract`: XDAMAGE_1_1_INTERFACE、Damage/XID、
  XDamageNotifyEvent 布局、XserverRegion 可用性
- 均不依赖 X server
