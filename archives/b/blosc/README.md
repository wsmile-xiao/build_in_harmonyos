# c-blosc — OpenHarmony 编译档案

## 软件简介
c-blosc 是高性能块压缩库，设计用于在 CPU 缓存层级高效压缩数据。

## 功能概述
- 多线程压缩/解压
- 支持多种压缩算法（blosclz, lz4, snappy, zlib, zstd）
- 零拷贝操作

## OHOS 适配要点
- CMake 标准构建
- 推荐使用 PREFER_EXTERNAL_ZSTD=ON

## 依赖关系
- 可选依赖: zstd, lz4, snappy, zlib

## 参考资料
- [c-blosc GitHub](https://github.com/Blosc/c-blosc)
