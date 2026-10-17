# header-only 库的「多棵 include 根并排」安装范式 + 上游 configure 期联网拉 gtest 的 Conan 替换 + 朴素扫描 N 与实际注册用例数的口径差

> DRAFT-tiny-dnn-1.0.0a3-header-only-triple-include-root-and-network-gtest-substitution
> （知识库扩展草稿，路径 B）与 tiny-dnn 1.0.0a3 归档同 PR 交付 —— PR #11301。

## 场景一：上游 `install(DIRECTORY ...)` 只装一棵目录，但库内部用了两种包含风格

tiny-dnn 的顶层 `CMakeLists.txt` 是

```cmake
add_library(tiny_dnn INTERFACE)
install(DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/tiny_dnn DESTINATION include)
```

—— header-only，且**只 install `tiny_dnn/` 一棵目录**。但 `tiny_dnn/` 内部：

| 包含写法 | 例子 | 解析要求 |
|----------|------|----------|
| 角括号 | `#include <cereal/cereal.hpp>` | include 根上必须有 `cereal/` |
| 相对 include 根 | `#include "third_party/stb/stb_image.h"`（`tiny_dnn/util/image.h:42`）<br>`#include "third_party/gemmlowp/public/gemmlowp.h"`（`tiny_dnn/core/kernels/tiny_quantized_matmul_kernel.h:18`） | include 根上必须有 `third_party/` |
| 相对 include 根 | `#include "tiny_dnn/tiny_dnn.h"` | include 根上必须有 `tiny_dnn/` |

**按上游 CMake 装完，消费者必然 `fatal error: 'cereal/cereal.hpp' file not found`。**
这两种风格混用说明：那两棵目录在小写目录名意义上就是"库的一部分"，只是上游
把它们的安装交给了"使用者的构建系统恰好把仓库根放进 include 路径"这个隐含假设
（在仓库内 `add_subdirectory` 时成立，`install` 后不成立）。

**判定信号（写 `package()` 之前扫一遍）**：

1. 顶层 `add_library(<x> INTERFACE)` 或 `INTERFACE` 属性 → header-only；
2. `grep -rn '#include <' tiny_dnn/` 发现角括号包含了**本仓库内的另一棵目录**；
3. `install(DIRECTORY ...)` 的目录数 < 第 2 步里被包含的顶层目录数。

命中就把**每一棵被包含的顶层目录并排装进同一个 include 根**，消费者只给一个 `-I`：

```
include/
├── tiny_dnn/
├── cereal/
└── third_party/
```

并在 `test_package` 里**显式**用角括号拉入另两棵树（本包用
`<tiny_dnn/util/image.h>` + `<tiny_dnn/core/kernels/tiny_quantized_matmul_kernel.h>`），
把这条安装布局变成一条编译期断言，而不是"碰巧能编过"。

## 场景二：上游在 configure 期联网拉依赖，CI worker 不可联网

上游 `test/CMakeLists.txt` 里没有 `find_package(GTest)`，只有

```cmake
DownloadProject(googletest
  GIT_REPOSITORY https://github.com/google/googletest.git
  GIT_TAG        master)
```

—— **在 configure 期 git clone 上游 master**。两个问题：CI worker 不联网；
`GIT_TAG master` 本身不可复现（今天拉到的和上周不是同一份）。

替换方式（照本仓库 cppnumericalsolvers/glaze 系列的既有做法）：

```python
def requirements(self):
    self.test_requires("gtest/1.17.0#<revision>")     # ohpcd 已发布

def build(self):
    gt = self.dependencies["gtest"].cpp_info
    gt_inc = " ".join('-I"{}"'.format(p) for p in gt.includedirs)
    gt_lib = gt.libdirs[0]
    self.run('"{}" -std=c++17 ... {} -L"{}" -lgtest -pthread -o "{}"'
             .format(cxx, gt_inc, gt_lib, exe))
```

要点：

- `requirements()` 里用 **`test_requires`** 而非 `requires`：header-only 库本身
  零依赖，gtest 只在 build() 里用，不该进 package 的依赖图
  （同时 `package_id()` 里 `self.info.clear()`）。
- **`-std` 要提**：上游声明 C++11，但 gtest 1.15+ 硬要求 C++14/17
  （否则 `gtest-port.h: C++ versions less than C++14 are not supported`）。
  提标准**不需要改上游源码一行**，是纯编译参数变更；在 notes.md 里明确写清
  "上游源码零改动"。
- 上游测试若用相对路径读数据（本包 `test/testhelper.h` 的 `resolve_path()`
  只试 `""` / `"./test/"` / `"../test/"` …），**运行时的 `cwd` 必须是源码根**，
  而不是 `build_folder`。

## 场景三：朴素文本扫描的 N ≠ 实际注册的用例数（rule4 口径）

钉版 `v1.0.0a3` 的 `test/` 目录里 `grep -o "TEST(" | wc -l` = **267**，
但真正注册进 gtest 二进制的只有 **199** 个（`clang++ -E -P` 预处理后统计
`class *_Test : public ::testing::Test` 恰为 198，加 `test_no_duplicate_symbols.cpp`
的 1）。差 68 全部可归因：

| 类别 | 数 | 原因 |
|------|----|------|
| `test_average_unpooling_layer.h` | 4 | `test/test.cpp:41` 被上游自己注释掉（`// TODO(yida): fix broken test`），默认构建不编译 |
| `test_caffe_converter.h` | 14 | `#ifdef CNN_USE_CAFFE_CONVERTER` 门控，需 Caffe protobuf |
| 落在 `#ifdef CNN_USE_NNPACK` 内 | 11 + 8 + 8 + 5 | `test_deconvolutional_layer.h` / `test_quantized_convolutional_layer.h` / `test_quantized_deconvolutional_layer.h` / `test_quantized_fully_connected_layer.h`。NNPACK 是 **Intel CPU** 加速后端 |
| 落在 `#ifdef CNN_USE_AVX` / `NNPACK` 内 | 11 | `test_convolutional_layer.h`（AVX 是 x86 指令集） |
| 其余被 `#ifdef` 屏蔽 | 2 + 2 + 1 + 1 + 1 | `test_max_pooling_layer.h` 2、`test_tensor.h` 2、`test_network.h` 1、`test_fully_connected_layer.h` 1、`test_core.h` 1 |

**这条对 rule4 直接有用**：评审的"上游实测 N"是**朴素文本扫描**，它会数到
`#ifdef CNN_USE_NNPACK` / `CNN_USE_AVX` 里那些在 aarch64 上**永远不可能启用**的
用例。所以

1. 声明 N 取**上游默认分支 master** 的朴素扫描值（本包 346），不是钉版值；
2. 未执行数 = 声明 N − 实跑数，并且**必须能逐类归因**（本包 147 = 79 master
   新增 + 68 钉版内未注册）；
3. 别把"实际注册 199"当成上游全集去声明 —— 那会在"少报"上翻车。

判定"实际注册数"的**可复现命令**（不需要跑 aarch64 二进制）：

```bash
clang++ --target=aarch64-linux-ohos --sysroot=$SYSROOT -std=c++17 -E -P \
        -I<src> -I<gtest>/include -I<src>/test <src>/test/test.cpp \
  | grep -cE 'class [A-Za-z_0-9]+_Test : public ::testing::Test'
```

（`grep -c "TEST("` 在预处理产物上恒为 0 —— `TEST` 是宏，会被展开掉。）

## 场景四：header-only 的"绿但空转"防护

header-only 库的 `build()` 里如果只写"编译通过"，一个配置漂移就能让测试静静地
一个都不跑而仍然绿。本包在解析 gtest 汇总行后加了**双重硬校验**：

```python
if failed != 0 or passed != ran:  raise ...   # 全绿
if ran < MIN_UPSTREAM_TESTS:      raise ...   # 用例集没缩水（本包 180，实测 199）
```

同时 preprocessed 统计（场景三）与 `llvm-nm --demangle | grep -c '::TestBody()$'`
互为独立佐证，用来确认 `ran` 不是被某个空 filter 骗出来的。
