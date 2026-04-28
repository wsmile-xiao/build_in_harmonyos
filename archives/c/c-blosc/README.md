# c-blosc

## 简介
c-blosc 是一个高性能、无损压缩库，支持多种压缩算法（blosclz, lz4, zlib, zstd）和 shuffle/bitshuffle 优化。

## OHOS 适配
- 使用 CMake 构建
- 需添加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` 兼容旧版 cmake_minimum_required
- 需设置 `-DBUILD_BENCHMARKS=OFF` 禁用依赖 clock_gettime 的 benchmark
- 硬件加速 shuffle (AVX2/SSE2) 不可用，使用 generic 实现

## 排除与替代
无。

## 依赖
无外部依赖（内置 LZ4 1.9.4, zlib 1.3.1, ZSTD 1.5.6）。

## 功能验证
```bash
pkg-config --modversion blosc  # 输出: 1.21.6
```

## 参考
- 官网: https://github.com/Blosc/c-blosc
