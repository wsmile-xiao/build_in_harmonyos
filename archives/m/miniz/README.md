# miniz

## 简介

miniz 是一个轻量级纯 C（C90）压缩 / ZIP 库，提供 zlib 兼容 API
（`mz_compress` / `mz_uncompress` / `mz_compressBound` / `mz_adler32` / `mz_crc32`）
以及完整的 ZIP 归档读写能力（`miniz_zip.c`）。无外部依赖，仅依赖 libc。

## 基本信息

- **名称**: miniz
- **主页 / 源码**: https://github.com/richgel999/miniz
- **当前适配版本**: 3.1.2
- **许可证**: MIT
- **分类**: library
- **构建系统**: cmake

## 鸿蒙适配要点

- 上游原生 CMake 非 amalgamation 路径在 OHOS aarch64 交叉编译下可直接构建，**无需补丁**
- miniz 与宿主 zlib (`libz.so`) 同名：强制 `BUILD_SHARED_LIBS=OFF` 静态库 (R26)，避免系统同名库冲突；消费方需定义 `MINIZ_STATIC_DEFINE`
- 关闭 `BUILD_EXAMPLES` / `BUILD_FUZZERS` / `BUILD_TESTS`（上游 Catch2 测试需 C++20），改用 test_package 消费者测试验证压缩能力
- 产物：`libminiz.a` + `include/miniz/` 头文件 + CMake package config（`miniz::miniz`）+ pkg-config（`miniz.pc`）

## 依赖关系

- 编译依赖：无（纯 C，仅 libc）
- 运行依赖：无

## 已编译版本

- 3.1.2 (2026-08-24)

## 参考资料

- 官网 / 源码: https://github.com/richgel999/miniz
- License: MIT
