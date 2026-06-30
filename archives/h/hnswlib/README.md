# hnswlib

## Description
hnswlib is a fast approximate nearest neighbor search library based on Hierarchical Navigable Small World (HNSW) graphs. It provides efficient similarity search for high-dimensional vectors.

## Versions
- 0.8.0 (2026-06-25): Header-only C++ library, CMake build system, **功能测试 23/23 PASS**

## Build Notes
- hnswlib is a header-only library (no .so/.a files)
- 安装产物: 7 header files + 1 CMake config file
- No external dependencies
- No patches required
- Build system: CMake (INTERFACE library)

## Functional Verification (OpenHarmony aarch64)
- **状态: ✅ 全部通过 (23/23)**
- L2 空间 kNN 召回率: 1.0 (1000 向量, k=10, ef=50)
- InnerProduct 空间: 正常
- 序列化/反序列化: 结果完全一致
- 删除/恢复: 正常
- 索引扩容: 正常
- 过滤搜索: 正常
- 多线程并发: 4 线程 18486 次搜索无崩溃
- BruteforceSpace: 与暴力验证一致
- 平台兼容: ARM aarch64 标量路径, 无 SSE/AVX 依赖

