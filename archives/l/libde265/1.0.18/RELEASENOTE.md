# libde265 1.0.18 发布说明

**发布日期**: 2026-04-20  
**HarmonyOS平台编译版本**

## 新特性

- H.265/HEVC视频解码支持
- 多线程并行解码
- ARM64平台适配

## HarmonyOS平台适配

本版本已针对 HarmonyOS (HongMeng Kernel 1.12.0, aarch64) 进行以下适配：

1. **ARM64汇编禁用**: ARM32汇编代码在ARM64平台不兼容，已禁用相关优化
2. **libc++链接修复**: 针对musl libc + libc++环境的链接问题修复

## 补丁列表

- `0001-arm64-platform.patch`: ARM64平台禁用ARM汇编
- `0002-libcpp-link.patch`: libc++标准库显式链接

## 测试结果

- 功能测试通过率: 100% (15/15)
- 核心API全部验证正常
- 多线程解码功能可用

## 已知限制

- dec265工具需要设置LD_LIBRARY_PATH或正确的RPATH

## 许可证

- 库: LGPL-3.0-or-later
- 示例程序: MIT