# xf86-video-ati

X.Org video driver for ATI/Radeon graphics hardware — a loadable module pair
for the X.Org X server.

## 功能概述

- 提供 ATI/Radeon GPU 的 2D/EXA 加速与 KMS 显示路径驱动
- 产出两个可加载模块：`ati_drv.so`（传统 ATI 驱动）和 `radeon_drv.so`（Radeon KMS 驱动）
- 支持 Radeon HD 2000-8000 系列（R600-Cayman）及更早的 ATI 显卡
- 通过 X server 的 dlopen 机制加载（模块符号由 server 进程提供，不可被独立程序链接）

## OHOS 适配

- **构建系统**：autotools（官方发布 tarball 自带全部生成文件，直接 `./configure && make`）
- **源码**：freedesktop.org 官方发布 tarball（含 configure/Makefile.in/config.guess/config.sub，无需 autoconf/automake）
- **补丁策略**：仅 3 个可移植性补丁（E007 config.guess/config.sub 的 HarmonyOS 三元组；E011 configure 的 HMDFS umask 修复）
- **xorg-server SDK 配方内生成**：xorg-server 尚无 conan 配方（registry 无记录），但每个 X.Org DDX 驱动都必须用其 SDK 头文件 + xorg-server.pc 编译。方案与已合入的 `xf86-video-fbdev` 先例一致并更进一步：配方内下载 xorg-server 21.1.15 官方 tarball，跑其自带 configure（全部 DDX 禁用，仅依赖已发布包）生成**真实的** xorg-server.h/dix-config.h，再按 meson install_data 清单采集 SDK 头集合 + 补全 5 个 XORG-DDX 宏，并合成 xorg-server.pc。xorg-server conan 包发布后可换回普通 `self.requires()`
- **cpp 包装器**：OHOS clang 不隐式读 stdin（裸 `clang -E` 报 no input files），会打断 xserver configure 的 RAWCPP 探测 — 配方在构建目录写一个 `cpp` 包装器（`clang -E -x c -`）前置到 PATH
- **--disable-glamor**：glamor 硬性依赖 gbm（mesa），OHOS PC 无 mesa；EXA/KMS 路径不受影响。禁用后驱动源码内全部 gbm 符号引用被 USE_GLAMOR 守卫编译掉（nm -D 实测双模块零 gbm 符号）；radeon_dri3.c 残留的 `#include <gbm.h>` 由 sdkdir 内的文档化桩头满足（无任何 gbm 代码被链接）
- **合成 .pc**：conan 的 libdrm 包把组件库合并为单个 libdrm.pc — 配方为上游 configure 合成 `libdrm_radeon.pc`；同理合成 `pciaccess.pc`（conan 包名 libpciaccess）；SDK configure 的无条件 REQUIRED_LIBS 成员 `xfont2` 以元数据桩 pc 满足（DDX 驱动 SDK 从不使用 xfont2，无任何链接）
- **make -j1**：E074 HMDFS jobserver fifo EPERM

## 依赖关系（2026-09-17，conan download -r=ohpcd 实测）

| 依赖 | conan 制品仓 | 说明 |
|------|-------------|------|
| libdrm | ✅ 2.4.133 | DRM 用户态库（libdrm + libdrm_radeon），驱动直接链接 |
| libpciaccess | ✅ 0.19 | PCI 总线访问库，驱动直接链接 |
| pixman | ✅ 0.46.4.3 | 像素库（X server SDK 头文件包含） |
| xorgproto | ✅ 2025.1 | X 协议头文件（xproto/fontsproto/xf86driproto/randrproto/...） |
| xorg-server | 构建期 SDK 生成 | SDK 头 + xorg-server.pc 由配方内从官方 21.1.15 tarball 生成（非 conan 依赖、不打包） |
| xtrans / libxau / libxkbfile / libxshmfence / nettle | ✅（各版本见版本级 manifest） | xorg-server SDK configure 的构建期输入，不进入驱动链接与打包 |
| libudev | — | 可选，configure 自动禁用 |

## 产物

```
lib/xorg/modules/drivers/ati_drv.so
lib/xorg/modules/drivers/radeon_drv.so
```

## 参考资料

- 源码：https://gitlab.freedesktop.org/xorg/driver/xf86-video-ati
- 官方发布：https://xorg.freedesktop.org/archive/individual/driver/xf86-video-ati-22.0.0.tar.xz
- xorg-server SDK 源（构建期）：https://www.x.org/releases/individual/xserver/xorg-server-21.1.15.tar.xz
- 版本：22.0.0
