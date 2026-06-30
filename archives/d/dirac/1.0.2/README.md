# dirac 1.0.2 — OpenHarmony 预编译包

## 简介
Dirac 是一个通用视频编解码器，面向从 QCIF 到 UHDTV 8K 的各种分辨率。它采用小波变换压缩技术，支持渐进式和隔行扫描视频。

## 编译信息
- **版本**: 1.0.2
- **构建系统**: autotools
- **平台**: aarch64-unknown-linux-ohos
- **编译器**: clang/clang++ (clang-15)
- **编译日期**: 2026-06-12
- **状态**: published

## 安装产物
- **二进制文件**: 24个
  - dirac_encoder: Dirac 视频编码器
  - dirac_decoder: Dirac 视频解码器
  - dirac_instrumentation: 编码诊断分析工具
  - 18个色彩空间转换工具 (RGB↔YUV, YUV↔UYVY等)
- **动态库**: libdirac_encoder.so, libdirac_decoder.so
- **头文件**: 7个 (libdirac_encoder, libdirac_decoder, libdirac_common)

## 使用方法

### 编码
```bash
dirac_encoder -CIF -qf 7.0 input.yuv output.drc
```

### 解码
```bash
dirac_decoder output.drc decoded.yuv
```

### 支持的分辨率预设
QSIF, QCIF, SIF, CIF, 4CIF, 4SIF, SD480, SD576, HD720P, HD1080I/P, UHDTV 4K/8K, Digital Cinema 2K/4K

## 编译适配补丁
1. configure: SHELL/cl精确匹配/umask修复/clang++注入-Wno-c++11-narrowing
2. mot_comp.cpp: static_cast修复C++11 narrowing
3. config.guess: 替换为识别ohos的版本
4. config.sub: 替换为识别ohos的版本
5. dirac-stdint.h: stdint定义修复

## 许可证
MPL-1.1 OR GPL-2.0-only OR LGPL-2.1-only
