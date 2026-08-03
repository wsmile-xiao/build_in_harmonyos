# c-blosc2

## 简介
c-blosc2 是新一代高性能、无损压缩库，支持多种压缩算法（blosclz, lz4, zlib, zstd）
和 shuffle/bitshuffle 优化，是 c-blosc 的升级版。

## OHOS 适配
- 使用 CMake 构建（cmake_minimum_required 3.16.3，无需 policy 兼容参数）
- 启用 BUILD_TESTS（完整运行上游 CTest 套件，1160 用例 100% 通过）
- 关闭 BUILD_BENCHMARKS（依赖 clock_gettime，OHOS 不可用）/ BUILD_FUZZERS / BUILD_EXAMPLES / BUILD_PLUGINS
- 默认静态库（BUILD_STATIC=ON, BUILD_SHARED=OFF）
- 硬件加速 shuffle (AVX2/SSE2) 不可用，使用 generic/neon 实现

## 依赖
无外部依赖（内置 LZ4, zlib-ng, ZSTD 编解码器）。

## 构建
```bash
conan create archives/c/c-blosc2/2.23.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

## 参考
- 官网: https://github.com/Blosc/c-blosc2
