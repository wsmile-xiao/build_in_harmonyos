# GStreamer Bad Plugins for HarmonyOS

## 概述

gst-plugins-bad 在 HarmonyOS/OpenHarmony PC (aarch64) 上的 Conan 配方与适配记录。

**可用版本**:
- **1.28.3**: meson 构建，vendored gst-plugins-base 子项目模式

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | GStreamer Bad Plugins |
| 官网 | https://gstreamer.freedesktop.org/ |
| 下载 | https://gstreamer.freedesktop.org/src/gst-plugins-bad/ |
| 许可证 | LGPL |

## 版本状态

| 版本 | 状态 | 构建系统 | 备注 |
|------|------|----------|------|
| 1.28.3 | built | meson | 17 个库 + bad/base 插件；base 以子项目 vendor |

## 依赖

| 依赖 | 版本 | 来源 |
|------|------|------|
| gstreamer | 1.28.3 | 制品仓（静态库） |
| glib2 | 2.88.0 | 制品仓（静态库） |
| zlib | 1.3.1.1 | 制品仓（PIC 静态库 override） |
| gst-plugins-base | 1.28.3 | 官方 tarball（meson 子项目，未发布） |

## OHOS 适配要点

1. **gst-plugins-base vendor 构建**: 制品仓无 gst-plugins-base 包，将官方 tarball
   解压到 `subprojects/gst-plugins-base/`，bad 的 meson dependency() fallback 自动
   落位本地目录（与 gst-libav 配方同构，无 wrap 下载）。
2. **zlib PIC override**: zlib/1.3.1 静态库非 PIC，base 共享库链接报
   `R_AARCH64_ADR_PREL_PG_HI21 ... recompile with -fPIC`；override 到 1.3.1.1。
3. **glib-mkenums**: HNP 的 perl 脚本版损坏（无 /usr/bin/perl），
   通过 native file [binaries] 钉到 conan glib2 包的 python3 版。
4. **OHOS ELF 签名**: meson install 改写 DT_RUNPATH（链后字节修改）使 lld 嵌入的
   代码签名失效，loader 以 EACCES 拒载；package() 用 build 原始产物覆盖安装产物。
5. **消费端限制**: conan glib2/gstreamer 为纯静态包，每个 .so 内嵌一份副本，
   消费端调 gst_init() 会跨副本操作类型注册表并死锁；验证用 dlopen/dlsym。

## 平台不兼容插件（禁用）

- gl（OHOS GL 头文件冲突）
- opensles（Android 专用）
- webp（libwebp 静态库符号冲突）
- orc（制品仓无 orc 包）

其余插件由 meson auto 检测（依赖缺失自动跳过，上游默认行为）。
