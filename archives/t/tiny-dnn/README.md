# tiny-dnn — 轻量级 C++11 深度学习库

## 概述

tiny-dnn（tiny-dnn/tiny-dnn）是 header-only 的 C++11 深度学习库（BSD-2-Clause），
不依赖任何第三方框架，纯模板实现即可完成全连接/卷积/池化/反卷积/批归一化等
网络的前向与反向传播，并支持 int8 量化推理、JSON/Binary 模型序列化。

**本仓库适配版本**：1.0.0a3（HarmonyOS PC aarch64 / musl）

## 功能概述

- 网络模型：`network<sequential>` 与 `network<graph>`（`fc` / `conv` /
  `max_pool` / `ave_pool` / `dropout` / `slice` / `concat` / `lrn` /
  `batch_normalization` 等层，`tan_h` / `sigmoid` / `relu` 等激活函数）
- 训练：`train<Error>()`（分类）/ `fit<Error>()`（回归），
  优化器 `gradient_descent` / `momentum` / `adagrad` / `adam` / `rmsprop`
- 量化推理：`quantized_convolutional_layer` / `quantized_deconvolutional_layer` /
  `quantized_fully_connected_layer`，后端为内置的 gemmlowp（int8）
- 序列化：`network::to_json()` / `from_json()` 与 `save()` / `load()` /
  `fast_load()`（cereal 后端，JSON / Binary 两种格式）
- 工具：`tiny_dnn::image<>`（stb 读图）、张量/形状工具、Caffe 模型转换

## OHOS 适配要点

1. **头文件必须整棵发运三棵目录**：`tiny_dnn/` 内部同时用
   `<cereal/cereal.hpp>`（角括号，需 include 根）与
   `"third_party/gemmlowp/..."`、`"third_party/stb/..."`（相对 include 根）
   两种包含风格，而上游 CMake 的 `install(DIRECTORY .../tiny_dnn ...)`
   **只装 `tiny_dnn/`**。本包把 `tiny_dnn/`、`cereal/`、`third_party/`
   并排装进同一个 include 根，消费者只需一个 `-I`。
2. **上游测试只有一条联网通道**：`test/CMakeLists.txt` 用 DownloadProject 在
   configure 期从 GitHub 拉 googletest（`GIT_TAG master`），CI worker 不可
   联网。本包改用 ohpcd 上已发布的 `gtest/1.17.0`，在 `build()` 内编译
   `test/test.cpp` + `test/test_no_duplicate_symbols.cpp` 并**实跑**上游
   199 个用例，对 gtest 汇总行做硬校验（`passed == ran` 且 `ran >= 180`）。
3. **C++ 标准提升到 C++17**：上游声明 C++11，但 gtest 1.15+ 要求 C++14/17。
   **tiny-dnn 上游源码零改动**，仅编译参数变化。
4. **测试必须在源码根目录下运行**：`test/testhelper.h` 的 `resolve_path()`
   只认相对路径（`""` / `"./test/"` / `"../test/"` …），test_image 用例
   需要当前目录下有 `test/testimage/`。

## 依赖关系

- 编译依赖：无（header-only，仅需 libc/libc++ 与 pthread）
- 测试依赖：`gtest/1.17.0`（`test_requires`，仅构建期）
- 运行依赖：无

## 参考链接

- 上游仓库：https://github.com/tiny-dnn/tiny-dnn
- 本仓库版本笔记：`1.0.0a3/notes.md`
