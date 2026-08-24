# grokj2k 20.3.6 适配笔记

## 库简介

Grok JPEG 2000 — 开源 JPEG 2000 编解码器，支持 Part 1（core）和 Part 15（HTJ2K）。
由 Grok Image Compression Inc. 维护，是 OpenJPEG 的高性能替代方案。

- **上游仓库**: https://github.com/GrokImageCompression/grok
- **版本**: 20.3.6（tag v20.3.6）
- **许可证**: AGPL-3.0（GNU Affero General Public License v3）
- **构建系统**: CMake（最低 3.21）
- **C++ 标准**: C++23

## 构建产物

| 产物 | 名称 | 说明 |
|------|------|------|
| 核心库 | libgrokj2k | JPEG 2000 编解码核心 |
| 编解码库 | libgrokj2kcodec | 高层编解码 API（本配方未构建） |
| CLI 工具 | grk_compress/decompress/dump/transcode | 命令行工具（本配方未构建） |

## 依赖情况

所有第三方依赖均内置（bundled），零外部依赖：

| 依赖 | 来源 | 说明 |
|------|------|------|
| zlib | thirdparty/libz | 压缩 |
| libpng | thirdparty/libpng | PNG 格式支持 |
| libtiff | thirdparty/libtiff | TIFF 格式支持 |
| libjpeg-turbo | thirdparty/或 FetchContent | JPEG 格式支持 |
| lcms2 | thirdparty/liblcms2 | 色彩管理 |
| highway | src/lib/core/highway (submodule) | SIMD 加速 |
| spdlog | src/include/spdlog (submodule) | 日志 |
| taskflow | src/include/taskflow (submodule) | 并行任务调度 |
| CLI11 | src/include/CLI11 (submodule) | CLI 参数解析 |

系统依赖：pthreads, atomic

## GitHub Archive 不含子模块

GitHub 自动生成的 archive tarball（`archive/refs/tags/`）不包含 git submodule 内容。
上游 CI 使用 `git-archive-all` 生成 `source-full.tar.gz`（release asset），但该文件较大。

本配方策略：下载主 archive + 逐个下载 4 个 submodule archive，在 `source()` 中注入到正确路径。

## 可选特性裁剪

| 特性 | 默认值 | 配方值 | 原因 |
|------|--------|--------|------|
| GRK_BUILD_CODEC | ON | OFF | 不构建 CLI 工具 |
| GRK_BUILD_DCI | OFF | OFF | DCI 支持不需要 |
| GRK_BUILD_CORE_EXAMPLES | ON | OFF | 不需要示例 |
| GRK_BUILD_CORE_SWIG_BINDINGS | ON | OFF | 不需要 Python 绑定 |
| GRK_BUILD_PLUGIN_LOADER | OFF | OFF | GPU 插件不需要 |
| GRK_ENABLE_LIBCURL | OFF | OFF | 网络功能不需要 |
| BUILD_TESTING | OFF | OFF | 测试需要测试数据集 |
| GRK_ENABLE_ASAN | OFF | OFF | 地址消毒器 |

## C++23 兼容性风险

grokj2k 要求 C++23（`set(CMAKE_CXX_STANDARD 23)`）。OHOS 上的 clang 15
可能不完全支持 C++23 特性。如果编译失败，可能需要：
1. 降级到 C++20（patch CMakeLists.txt）
2. 添加 `-std=c++2b` 编译标志

## 上游测试

上游测试需要 `grok-test-data`（大型二进制测试语料），通过 `GRK_DATA_ROOT` 环境变量指定。
本配方禁用上游测试（`BUILD_TESTING=OFF`），test_package 通过 `grk_version()` API 验证链接。

## 已知限制

- 静态库构建（不构建 .so）
- 不构建 CLI 工具（grk_compress 等）
- 不构建 SWIG 绑定
- 上游测试未运行（需要测试数据集）
- C++23 兼容性待真机验证
