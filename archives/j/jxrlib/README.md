# jxrlib — JPEG XR 编解码库

## 简介
jxrlib 是微软发布的 JPEG XR（也称 HD Photo / Windows Media Photo）开源编解码库。
它提供 C 语言实现的 JPEG XR 图像压缩/解压缩功能，适用于嵌入式和桌面平台。

## 主要组件
- **libjpegxr.a** — JPEG XR 核心编解码算法库（静态）
- **libjxrglue.a** — JPEG XR 接口适配层 + 测试工具库（静态）
- **JxrEncApp** — JPEG XR 编码命令行工具
- **JxrDecApp** — JPEG XR 解码命令行工具

## 编译信息
- 构建系统: makefile
- 编译器: clang (LLVM 15.0.4)
- License: BSD-2-Clause
- 无外部依赖

## 支持平台
- OpenHarmony / 鸿蒙 (aarch64)
