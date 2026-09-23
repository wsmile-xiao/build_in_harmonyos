# tiny-dnn 1.0.0a3 — HarmonyOS PC 适配笔记

## 1. 概览

| 项 | 值 |
|----|----|
| 上游 | https://github.com/tiny-dnn/tiny-dnn |
| 版本 | 1.0.0a3（git tag `v1.0.0a3`，commit `2a2b50caa437`） |
| 源码 | `https://github.com/tiny-dnn/tiny-dnn/archive/refs/tags/v1.0.0a3.tar.gz` |
| SHA256 | `e2c61ce8c5debaa644121179e9dbdcf83f497f39de853f8dd5175846505aa18b` |
| 构建 | header-only（`add_library(tiny_dnn INTERFACE)`；无编译产物） |
| 包类型 | header-library |
| 依赖 | 无（运行时零依赖）；测试期 `test_requires gtest/1.17.0` |

## 2. 头文件布局：为什么必须整棵发运三棵目录

tiny-dnn 的 `tiny_dnn/` 树内部同时使用两种包含风格：

- **角括号**：`#include <cereal/cereal.hpp>` —— 需要 include 根上有 `cereal/`
- **相对 include 根**：`#include "third_party/gemmlowp/public/gemmlowp.h"`
  （`tiny_dnn/core/kernels/tiny_quantized_matmul_kernel.h:18`）与
  `#include "third_party/stb/stb_image.h"`（`tiny_dnn/util/image.h:42`）

而上游 `CMakeLists.txt` 的安装规则是：

```cmake
install(DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/tiny_dnn DESTINATION include)
```

**只装 `tiny_dnn/`**。被它包含的 `cereal/` 与 `third_party/` 不在安装列表里，
消费者按上游 CMake 装完必然 `fatal error: 'cereal/cereal.hpp' file not found`。

本包在 `package()` 里把三棵目录**并排装进同一个 include 根**：

```
include/
├── tiny_dnn/     库本体（内部写 "tiny_dnn/..." 与 "third_party/..."）
├── cereal/       序列化后端（被以 <cereal/...> 角括号包含）
└── third_party/  gemmlowp / stb / CLCudaAPI / cl_kernels
```

消费者只需要一个 `-I<include 根>`。
`test_package/test_tiny_dnn.cpp` 刻意同时用 `<tiny_dnn/util/image.h>` 与
`<tiny_dnn/core/kernels/tiny_quantized_matmul_kernel.h>` 显式拉入另两棵树，
把这条安装布局变成一条**编译期**断言。

## 3. 测试：上游的 gtest 可执行文件怎么在 CI 上跑起来

上游 `test/CMakeLists.txt` 只有一条测试通道，且它在 **configure 期联网**：

```cmake
DownloadProject(googletest
  GIT_REPOSITORY https://github.com/google/googletest.git
  GIT_TAG        master)
```

CI worker 不可联网，且 `GIT_TAG master` 本身也不可复现。本包改用 ohpcd 上已
发布的 `gtest/1.17.0`，在 `build()` 内直接编译并**实跑**：

- 源文件：`test/test.cpp` + `test/test_no_duplicate_symbols.cpp`
  （前者用 `#include "test_xxx.h"` 把 24 个测试头编进同一个 TU）
- 标准：`-std=c++17`（上游声明 C++11，但 gtest 1.15+ 要求 C++14/17；
  **tiny-dnn 上游源码零改动**）
- 告警：只压 `-Wno-unused-value` 这一条 —— 上游
  `test/test_serialization.h:430` 的 `s1 << (f2, f3) << c4;` 是逗号运算符笔误
- 运行目录：`cwd = source_folder` —— `test/testhelper.h` 的 `resolve_path()`
  只认相对路径（`""` / `"./test/"` / `"../test/"` …），
  test_image 用例需要 `test/testimage/` 就在当前目录下
- 结果校验：解析 gtest 汇总行（`[==========] N tests from M test suites ran` /
  `[  PASSED  ] N tests` / `[  FAILED  ] N tests`），
  要求 **failed == 0 且 passed == ran**，并且 `ran >= MIN_UPSTREAM_TESTS`
  （防"绿但空转"：配置漂移导致只跑了个位数时直接判失败而不是静默通过）

## 4. 上游测试用例数的三个口径（rule4）

| 口径 | 数 | 说明 |
|------|----|------|
| 上游默认分支 master `test/` 朴素扫描 | **346** | PR body 声明的上游全集 N |
| 钉版 `v1.0.0a3` 的 `test/` 朴素扫描 | 267 | 钉版 tarball 实际含有的文本量 |
| 钉版实际**注册并实跑**的 gtest 用例 | **199** | `clang++ -E -P` 预处理后统计 `class *_Test : public ::testing::Test` = 198，加 `test_no_duplicate_symbols.cpp` 的 1 |

`未执行 147 = 346 − 199`，两个来源：

1. **79 = 346 − 267**：上游 master 相对钉版新增的文件/用例
   （`test_integration.h` 22、`test_node.h` 12、`test_optimizers.h` 7、
   `test_global_average_pooling_layer.h` 7、`test_rnn_cell.h` 4、
   `test_gru_cell.h` 2、`test_lstm_cell.h` 2、`test_activation_layer.h` 1、
   `test_l2_norm_layer.h` 1、`test_nms.h` 1、`test_zero_pad_layer.h` 1 = 60，
   以及既有文件在 master 上的净增 19）。钉版 tarball 里这些文件不存在。
2. **68 = 267 − 199**：钉版 `test/` 里被朴素扫描数到、但**不会注册为 gtest
   用例**的 `TEST(` 宏：
   - `test_average_unpooling_layer.h` **4**：`test.cpp:41` 被上游自己注释掉
     （`// TODO(yida): fix broken test`），默认构建就不编译
   - `test_caffe_converter.h` **14**：`#ifdef CNN_USE_CAFFE_CONVERTER` 门控，
     需要 Caffe protobuf 工具链
   - **50** 处落在未启用的 `#ifdef` 分支内：
     `#ifdef CNN_USE_NNPACK` 有 `test_deconvolutional_layer.h` 11、
     `test_quantized_convolutional_layer.h` 8、
     `test_quantized_deconvolutional_layer.h` 8、
     `test_quantized_fully_connected_layer.h` 5；
     `#ifdef CNN_USE_AVX` / `CNN_USE_NNPACK` 有
     `test_convolutional_layer.h` 11；
     其余 `test_max_pooling_layer.h` 2、`test_tensor.h` 2、`test_network.h` 1、
     `test_fully_connected_layer.h` 1、`test_core.h` 1。
     NNPACK 是面向 Intel CPU 的加速后端、AVX 是 x86 指令集，
     aarch64/OHOS 上都不适用。

## 5. OHOS 平台相关的可观测行为

- `tiny_dnn/config.h:80`：`#if !defined(_MSC_VER) && !defined(_WIN32) && !defined(WIN32)`
  时无条件 `#define CNN_USE_GEMMLOWP` —— OHOS 命中的是**内置 gemmlowp 的
  int8 量化路径**，而不是"没有量化实现"。
- `core::default_engine()` 在无 `CNN_USE_AVX` 时返回 `backend_t::internal`；
  aarch64 上没有 AVX，必须退到内部后端。
- `CNN_TASK_SIZE`（无 OpenMP 时为 **8**）是 `network::train` 的 `n_threads`
  默认值，批训练用 `std::thread` 起任务 —— OHOS 的 bionic 上必须可用，
  且固定种子 + `n_threads=1` 的结果必须逐位可复现。
- **`to_json()` / `from_json()` 只序列化架构，不序列化权重**：
  `network.h` 的 `to_json()` 内部走 `to_archive(oa, content_type::model)`，
  注释也写明是 "save the network architecture as json string"。所以
  `from_json()` 之后得到的是一个**未训练**的网络 —— 想连权重一起往返必须用
  `save()/load()` 配 `content_type::weights_and_model`（`file_format::json`
  走 cereal 的 JSON 归档）。消费者测试组 4 因此拆成两条：架构往返断言
  输出形状，weights_and_model 往返断言预测值逐位一致。
- 另：`fc<...>` 2 输出 + one-hot 语义下，`get_loss<mse>()` 的数值在训练中
  **不单调下降**（实测 2.0 → ~4.56 而分类 4/4 全对）—— 该配置下 loss 数值
  不是有效判据，只有 `predict_label()` 的分类结果才是。

## 6. 随包内容

- `include/{tiny_dnn,cereal,third_party}/`：三棵目录并排（上游源码零改动，
  `patches_applied: []`）
- `licenses/LICENSE`：上游 BSD-2-Clause

## 7. 复现命令

```bash
conan create . --version=1.0.0a3 -pr:h=ci/conan/profiles/ohos-aarch64
```
