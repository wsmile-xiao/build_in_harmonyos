# libxrandr 1.5.5.1 适配笔记

## 概述

X.Org RandR 扩展客户端库。提供 `XRR*` API 用于查询和修改屏幕分辨率、
旋转、反射、显示器热插拔与多显示器布局。产物 `libXrandr.so.2.2.0`
（`-version-number 2:2:0`，SOVERSION 2）。

## 版本与包名

- Conan 包名/版本：`libxrandr/1.5.5.1`（R37 版本后缀，上游源码版本 1.5.5）。
- 上游源码：`libXrandr-1.5.5.tar.xz`（2026-01-26 发布）。
- SHA256: `72b922c2e765434e9e9f0960148070bd4504b288263e2868a4ccce1b7cf2767a`。

## W0 依赖检查（R36）

在 `ohpcd` 验证（`conan download --only-recipe`）：

| 依赖 | 说明 | 状态 |
| --- | --- | --- |
| libx11/6.4.0 | 上游 libX11-1.8.10 源码，已发布 + OHOS armv8 二进制 | ✅ |
| libxext/6.4.0 | 上游 libXext-1.3.6 源码，已发布 + 二进制 | ✅ |
| libxrender/0.9.12 | 提供 xrender.pc + Xrender.h，已发布（recipe 钉 libx11/1.8.13） | ✅ |
| xorgproto/2025.1 | 提供 randrproto/xextproto/renderproto/xproto pc 模块 | ✅ |

> 任务描述的 "xorgproto/2024.1、libX11/1.8.10、libXext/1.3.6" 对应本仓库
> 已发布的 ABI 轨道包名：xorgproto/**2025.1**（2024.1 未发布）、
> libx11/**6.4.0**（源码即上游 1.8.10）、libxext/**6.4.0**（源码即上游 1.3.6）。
> 另需 libxrender/0.9.12：`configure.ac` 的 `PKG_CHECK_MODULES` 硬性要求
> `xrender` 模块，且源码 10 处 include `X11/extensions/Xrender.h`。

## 依赖轨道（重要陷阱）

制品仓 libxrender/0.9.12 的 recipe 钉 libx11/**1.8.13**，而 libxext/6.4.0 钉
libx11/**6.4.0**（cmd-pkgs 轨道，与已发布 libxi/libxscrnsaver/libxcursor 一致）。
必须在 recipe 里 `self.requires("libx11/6.4.0", force=True)`，让 libxext 命中
已发布二进制（免重建），libxrender/0.9.12 则对 6.4.0 重新源码构建（其
relocatable-libtool-metadata linker view 支持）。切勿改强制 1.8.13：该轨道
libX11.la 会引用 libxcb.la，而 libxcb/1.16 不带 .la，下游源码构建会报
`is not a valid libtool archive` 失败。

## 构建系统与 OHOS 适配

- **autotools**。1.5.5 发布包自带预生成 `configure`（GNU Autoconf 2.72），
  XORG 宏（XORG_DEFAULT_OPTIONS / MAN_SUBSTS）已内联 —— **无需 xorg-macros
  m4**，直接运行 configure（本仓库 `x/xorg-util-macros` 为空不影响）。
- **config.guess/config.sub**：config.sub (2024-07-27) 已内置
  `ohos*` / `linux-ohos-*`；config.guess 缺 HarmonyOS 分支，补丁 `0001`
  在 NetBSD 分支前插入 `*:HarmonyOS:*:*` → `aarch64-unknown-linux-ohos`。
- **umask**：上游 configure 用 `umask 077`，OHOS/HMDFS 下 config.status 无法
  在受限临时目录执行，recipe 生成 `configure-ohos`（umask 077→022）。
- **linker-view**：把依赖包 libdir 的 .a/.la/.so 复制到 build 目录私有
  linker-view 并改写 .la 的 libdir/dependency_libs（绝对路径 → 相对 -L + -l），
  规避 libtool 对 Conan 缓存旧 build 路径的解析失败。
- **shell**：OHOS 用 `/system/bin/sh` 运行 configure/make（`export
  SHELL/CONFIG_SHELL=/system/bin/sh`）。
- **configure args**：`--host=aarch64-linux-ohos --enable-shared
  --disable-static`（shared 默认；静态模式反之）。
- **make check**：上游无 TESTS/check_PROGRAMS，`make check` 为空目标。

## 源码修改（补丁）

### patches/0001-config.guess.patch

config.guess 添加 HarmonyOS 检测分支：

```sh
case $UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:$UNAME_VERSION in
    *:HarmonyOS:*:*)
        case $UNAME_MACHINE in
            aarch64|arm64) echo aarch64-unknown-linux-ohos; exit ;;
            *) echo "$0: unsupported HarmonyOS machine $UNAME_MACHINE" >&2; exit 1 ;;
        esac
        ;;
esac
```

## 产物

```
lib/libXrandr.so -> libXrandr.so.2.2.0
lib/libXrandr.so.2 -> libXrandr.so.2.2.0
include/X11/extensions/Xrandr.h
lib/pkgconfig/xrandr.pc
licenses/COPYING
```

`xrandr.pc` 的 prefix 在 package 阶段改写为 `${pcfiledir}/../..`（相对化），
安装的 `libXrandr.la` 被移除。

## test_package

- `api_surface.c`：链接期符号面探测（69 个 XRR* 入口点函数指针引用），
  无需 X server。
- `alloc_contract.c`：显示无关 ABI 契约 —— XRRAllocModeInfo/XRRFreeModeInfo、
  XRRAllocGamma/XRRFreeGamma（连续通道 stride）、RANDR 协议版本宏、
  XRRScreenSize 布局。
- OHOS 下对测试可执行文件做 `.codesign` 签名后运行。

## 验证结果

- `conan create`（OHOS aarch64, clang 15, Release）：**通过**，
  两个测试均 `PASS`。
- `conan-verify`：G0-G4 / L2/L4/L5 全 **PASS**。
- 产物基线：`libXrandr.so.2.2.0`（OHOS armv8）。

## 遗留问题

- `ohpcd` push 权限受限时，仅发布到本地 Conan 缓存，manifest 标 built；
  上游 CI 合并后由 release 流水线 upload。
---

**编译结束**: 2026-09-03 12:35
**最终状态**: built

---

## 1.5.5.1 版本说明（2026-09-08 增补）

**背景**：为 gtk 3.24.52 X11 后端适配发布 OHOS binary（R37 版本后缀）。制品仓
`libxrandr/1.5.5` 仅有 recipe、无 OHOS 预编译 binary（此前从未在 OHOS 构建），
gtk X11 后端依赖它（meson dependency xrandr >= 1.2.99）→ 发布 1.5.5.1 补齐。

**变更**：无源码/配方逻辑修改，仅版本号 1.5.5 → 1.5.5.1 并完成 OHOS aarch64
本地构建（autotools，config.guess patch 沿用 1.5.5；依赖 libx11/6.4.0、libxext、
libxrender、xorgproto 均已发布）。

**构建验证**：
```bash
conan create archives/l/libxrandr/1.5.5.1 --version=1.5.5.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```
test_package 真实调用 libXrandr API（XRRQueryExtension 等，R34）。

**编译日期**: 2026-09-08
**最终状态**: built（本地 W3 验证通过）
