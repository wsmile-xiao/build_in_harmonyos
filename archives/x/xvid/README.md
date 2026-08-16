# xvid

xvid 是 MPEG-4 视频编解码库，提供 ISO 兼容的高质量视频压缩和解压缩功能。

## 功能概述

- MPEG-4 视频编码和解码
- 支持多种编码模式（quantization, rate control）
- 高效的汇编优化（x86 SIMD）
- 纯 C 实现版本（跨平台兼容）

## OHOS 适配

- **构建系统**: autotools (configure/make)
- **关键补丁**: config.guess/config.sub 替换、umask 修复、SRC_DIR 路径修复
- **无官方测试套件**: 无 make check 目标

## 产物

- libxvidcore.so.4.3 (共享库, ELF aarch64)
- libxvidcore.a (静态库)
- xvid.h (头文件)

## 参考资料

- 源码: https://downloads.xvid.com/downloads/xvidcore-1.3.7.tar.gz
- 版本: 1.3.7
