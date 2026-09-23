# blosc2

## 简介

Blosc2 是 Blosc 新一代高性能、无损压缩库，提供 blosc2 API、B2ND/SChunk/Frame 能力以及多种内置编解码器。

## OHOS 适配

- 上游版本：3.2.3
- 构建系统：CMake，目标平台 OHOS/aarch64
- 默认产物：静态 libblosc2.a
- 上游测试：启用 BUILD_TESTS，最终 OHOS 配置串行执行 1194 项，全部通过
- 明确限制：test_stdio_validation 依赖 tmpfile()，因设备 /tmp 权限跳过 1 项
- 消费者测试：真实压缩/解压 round-trip 和 codec-name API，4 个断言通过

## 依赖

上游 CMake FetchContent 获取 LZ4、zlib-ng、ZSTD；Conan 配方不声明外部运行时依赖。

## 版本

详见 3.2.3/ 版本归档。
