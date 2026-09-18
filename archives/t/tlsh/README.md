# tlsh

TLSH（Trend Micro Locality Sensitive Hash）是一个模糊匹配库：为数据生成具有
相似度可比性的哈希值（digest），并给出两个 digest 之间的距离分数。
典型用途是恶意样本聚类、近似文档/文件检索等。

## Description

- 128 桶（BUCKETS_128）紧凑哈希 + 1 字节校验和，digest 为 `T1` + 70 位十六进制
- 距离计算支持「含长度」与「不含长度」两种口径
- 交付 C++ 库（`libtlsh.a`）+ 公共头文件 + 命令行工具 `tlsh`

## Versions

- 5.0.0 (2026-02-17): 官方 tag `5.0.0`；digest 默认带 `T1` 前缀

## Build System

CMake（上游根 `CMakeLists.txt`），无第三方依赖（仅 pthread）。

## Dependencies

None. Standalone build.

## Links

- GitHub: https://github.com/trendmicro/tlsh
