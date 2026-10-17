# abseil 20260526.0 (LTS) — HarmonyOS PC 适配笔记

## 概要

| 项 | 值 |
|----|----|
| 上游 | https://github.com/abseil/abseil-cpp |
| tag | `20260526.0`（LTS） |
| 源码 sha256 | `6e1aee535473414164bf83e4ebc40240dec71a4701f8a642d906e95bea1aea0c` |
| 构建系统 | CMake（≥3.16，`CMakeLists.txt:19`），C++17 |
| 目标 | OHOS / armv8 / clang 15 / libc++ / Release |
| 依赖 | 无外部 Conan requires（仅系统 pthread） |
| 补丁 | 无 |
| 上一适配版本 | 20240722.0（本版本为**新版本重新适配**） |

## 1. 包名与 ABI 关系（重要，避免误判为重复适配）

制品仓与源码仓同时存在**两个不同 Conan 包名**：

| 包名 | 版本 | 消费者 |
|------|------|--------|
| `abseil-cpp` | 20260107.1（另见 20240116.1） | protobuf/33.6、grpc 1.70.0 / 1.84.0 |
| `absl` | 20240722.0、**20260526.0（本包）** | 以 `absl/<ver>` 引用的历史消费者 |

两者是**不同的 Conan 引用**，不是重复适配。本配方沿用 `absl` 这一历史
包名，避免破坏已有消费者的引用；同时新增 20260526.0 版本，与既有的
20240722.0 并存。

ABI 提示：gRPC / protobuf 走的是 `abseil-cpp/20260107.1`（lts_20260107），
二者混链会有 ABI 冲突——下游应保持同一系。

## 2. HarmonyOS 适配要点

### 2.1 `ABSL_ENABLE_INSTALL` 必须显式打开

`CMakeLists.txt:39/41`：

```cmake
if(<not top-level>)
  option(ABSL_ENABLE_INSTALL "Enable install rule" OFF)
else()
  option(ABSL_ENABLE_INSTALL "Enable install rule" ON)
endif()
```

作为 Conan 子工程构建时它不是顶层，默认 **OFF**——不显式打开就不会安装
`lib/cmake/absl/abslConfig.cmake`。下游（例如 gRPC 1.84.0）依赖
`find_package(absl CONFIG)` 提供按组件命名的 `absl::<component>` target，
因此本配方显式 `ABSL_ENABLE_INSTALL=ON`。

### 2.2 lld 链接期需要 libxml2

OHOS SDK 的 lld 在运行期依赖 `libxml2.so.16`（位于 SDK 的
`ohos/native/llvm/lib`）。不注入该目录时，cmake 的编译器链接测试会以
`Error loading shared library libxml2.so.16` 失败。配方的 `environment()`
通过 `LD_LIBRARY_PATH` 注入该目录。

### 2.3 测试开关是双重的

`CMakeLists.txt:136`：

```cmake
if((BUILD_TESTING AND ABSL_BUILD_TESTING) OR ABSL_BUILD_TEST_HELPERS)
```

必须**同时**满足 `BUILD_TESTING` 与 `ABSL_BUILD_TESTING`，只关一个不足以
跳过测试目标。本配方两个都显式关闭。

## 3. 构建配置

```
-DCMAKE_BUILD_TYPE=Release
-DABSL_ENABLE_INSTALL=ON
-DABSL_PROPAGATE_CXX_STD=ON
-DABSL_BUILD_TESTING=OFF
-DBUILD_TESTING=OFF
-DBUILD_SHARED_LIBS=OFF
```

## 4. 测试：诚实申报

### 4.1 上游测试（未运行，如实申报）

| 项 | 值 |
|----|----|
| 框架 | GoogleTest |
| 规模 | `*_test.cc` **252** 个；另 `*_benchmark.cc` 49 个（基准，非自动套件） |
| 分布（部分） | strings 53、random 37、base 31、container 29、log 21、time 12、debugging 11、flags 11、synchronization 10、status 5、hash 4、numeric 3 |
| 本次执行 | **未执行（NOT_RUN）** |

未执行的技术原因：

1. **测试依赖不可得**：absl 的 CMake 测试目标需要外部 GoogleTest
   （`CMakeLists.txt:109-148`，默认路径 `/usr/src/googletest`，否则从
   GitHub 拉取）。farm 构建机上没有该依赖，而按规则不应为了跑测试
   在构建期引入网络下载。
2. **规模不可行**：252 个测试文件，在 farm 的单线程构建约束
   （profile `tools.build:jobs=1` + `CMAKE_BUILD_PARALLEL_LEVEL=1`）下
   属于不可行量级。
3. 旧版本（20240722.0）曾实测过 29 个核心测试文件共 896 用例
   （881 passed / 13 failed / 2 skipped，2 项因 libc 差异失败），
   那是**针对 20240722.0** 的结果；本版本未复跑，故**不引用旧结论**。

本版本如实申报 NOT_RUN，不把未运行的测试计为 PASS。

### 4.2 test_package（已执行，消费者视角）

`test_package/test_absl.cpp`（2 个断言）：

| # | 动作 | 断言 |
|---|------|------|
| 1 | `absl::StrCat("absl-", 20260526, "-ok")` | 结果 == `"absl-20260526-ok"` |
| 2 | `absl::SimpleAtoi("42", &v)` | 返回 true 且 v == 42 |

通过 `self.run` 用 `/data/service/hnp/bin/clang++` 直接编译链接执行，
`-Wl,--start-group` 链接包内**全部** `libabsl_*.a` 组件库，以验证
组件间内部依赖链（SimpleAtoi → raw_log_internal 等）在 OHOS 上可解析。
测试二进制为 aarch64，在 OHOS PC 上原生运行。

## 5. 产物

`include/absl/**` 公共头、`lib/libabsl_*.a`（按组件，共 21 个组件目录）、
`lib/cmake/absl/abslConfig.cmake`（按组件 target 的 CMake 包配置）。

绝大部分组件是 header-only；有编译产物的组件（strings、status、time、
synchronization、log、flags、random、hash、debugging、base、numeric 等）
以静态库形式交付。

## 6. 参考

- 上一版本配方：`archives/a/absl/20240722.0/`（作为演进基线）
- 相关包：`archives/a/abseil-cpp/20260107.1/`（protobuf/grpc 使用的包名）
- 上游：https://abseil.io
