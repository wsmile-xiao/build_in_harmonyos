# aklomp-base64 0.5.2 适配笔记

## 库简介

Fast Base64 stream encoder/decoder，C99 实现，支持 SIMD（AVX2/NEON 等）加速。
OHOS aarch64 适配开启 NEON64 原生 SIMD（NEON64_CFLAGS=-march=armv8-a），其他架构回退纯 fallback。

## 关键构建选项

| 选项 | 说明 |
|------|------|
| make lib/libbase64.o | 产出单个自包含对象文件 |
| ar rcs libbase64.a | 打包为静态库 |

## 产物

- 静态库：libbase64.a
- 头文件：include/libbase64.h

## 验证

- test_package：编解码往返一致（"Hello, World!" ↔ SGVsbG8sIFdvcmxkIQ==）
- 依赖：无（纯 libc）
