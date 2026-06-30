# ffmpeg 5.1.6 编译笔记

## 编译概要

**软件**: ffmpeg  
**版本**: 5.1.6  
**编译日期**: 2026-05-22  
**状态**: built  
**构建系统**: autotools

## 平台适配

### 问题

ffmpeg configure 脚本在原始版本中不识别 HarmonyOS 操作系统，导致 configure 失败报错 "Unknown OS 'harmonyos'"。

### 解决方案

修改 `configure` 文件，在第 5645 行将 `linux)` 改为 `harmonyos|linux)`，使 HarmonyOS 被识别为合法的操作系统，并共享 Linux 的配置选项。

**补丁文件**: `patches/0001-configure.patch`

**修改详情**:
```diff
-    linux)
+    harmonyos|linux)
         enable section_data_rel_ro
         enabled_any arm aarch64 && enable_weak linux_perf
```

## 编译配置

**Configure 参数**: `--prefix=/storage/Users/currentUser/usr/local`

**编译特性**:
- 静态构建
- pthreads 线程支持
- 网络支持
- 外部库: iconv, zlib
- 硬件加速: v4l2_m2m, vulkan
- 程序: ffmpeg, ffprobe
- 库: avcodec, avformat, avutil, avfilter, avdevice, swresample, swscale

## 编译过程

1. **初始化**: 使用 `ohc-run.py init-build` 下载并解压源码
2. **预扫描**: 检测到 pthread_cancel 在 musl/OHOS 上不可用（PSCAN-MUSL-001），但 ffmpeg 不使用此函数，不影响编译
3. **Configure**: 应用 patch 后成功 configure
4. **编译**: `make -j1` 成功编译，生成 ffmpeg 和 ffprobe 二进制文件
5. **安装**: `make install DESTDIR=$TEST_PREFIX` 安装到 staging 目录
6. **打包**: 使用 `ohc-run.py package` 生成 tar.gz 文件
7. **质量门禁**: verify-build 通过（G1-G4 检查全部通过）

## 编译产物

**打包文件**:
- `ffmpeg-5.1.6-ohos-aarch64.tar.gz` (214MB) - Release 版本
- `ffmpeg-5.1.6-ohos-aarch64-debug.tar.gz` (54KB) - Debug 符号文件

## 备注

ffmpeg 5.1.6 是 5.x 系列的最新稳定版本。configure 脚本原本已经包含对 harmonyos 的支持（第 5655 行），但该 case 分支的位置在错误处理分支之前，导致实际编译时仍会报错。通过将 `harmonyos|linux` case 提前到正确位置解决了此问题。

---
**编译结束**: 2026-05-22 12:01  
**最终状态**: built