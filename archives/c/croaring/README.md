# CRoaring

CRoaring 是 Roaring Bitmap 的 C/C++ 实现，提供高性能的压缩位图操作。

## 功能概述

- 高性能压缩位图（Roaring Bitmap）
- 支持位集合的并集、交集、差集等操作
- 支持序列化和反序列化
- C 和 C++ API

## OHOS 适配

- CMake 构建，使用 `-DENABLE_ROARING_TESTS=OFF` 禁用测试
- 编译成功，状态为 success

## 依赖关系

- C/C++ 编译器

## 参考资料

- 官网: https://roaringbitmap.org/
- 源码: https://github.com/RoaringBitmap/CRoaring
