# ISA-L Crypto

## 简介
ISA-L Crypto（Intel Storage Acceleration Library - Crypto）是 Intel 提供的存储加密加速库，支持多缓冲区 AES-GCM/XTS、SHA256/MD5 哈希等功能。在 ARM 平台上使用 C 基础实现，性能优化有限。

## OHOS 适配
- 同时支持 autotools 和 CMake 构建，CMake 对 aarch64 更友好
- 缺少 automake 时使用 CMake 构建即可
- 缺少 OpenSSL 头文件时需禁用测试（BUILD_TESTS=OFF）和性能测试（BUILD_PERF=OFF）
- aarch64 平台使用 base C 实现，无 SIMD 汇编优化
- 生成 libisal_crypto.so 共享库及 13 个头文件

## 依赖
- 编译依赖：cmake, clang
- 运行依赖：libc

## 功能验证
```bash
# 检查库安装
ls -la $HOME/usr/local/lib/libisal_crypto*
```

## 参考
- 源码：https://github.com/intel/isa-l_crypto
- 文档：https://intel.github.io/isa-l_crypto/
