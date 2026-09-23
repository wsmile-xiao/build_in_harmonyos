# onnxruntime 1.29.1 — HarmonyOS PC 适配笔记

## 概要

| 项 | 值 |
|----|----|
| 上游 | https://github.com/microsoft/onnxruntime |
| tag | `v1.29.1` |
| 源码 sha256 | `aba6ff915ffa3689af9bd6a84102a221ad35427e602f22bb18ae8323997d0f0d` |
| 构建系统 | CMake（**≥3.28**，`cmake/CMakeLists.txt:6`），**C++20** |
| 目标 | OHOS / armv8 / clang 15 / libc++ / Release |
| 依赖 | 全部由 FetchContent 拉取（镜像预下载）；宿主 protoc 由 protobuf v21.12 现场构建 |
| 补丁 | 8 个（其中 0003/0005 已针对 1.29.1 **重新生成**） |
| 上一适配版本 | 1.27.1（本版本为**新版本重新适配**，逐项重新核验） |

## 1. 与 1.27.1 的差异（重新核验结果）

### 1.1 构建门槛提升

| 项 | 1.27.1 | 1.29.1 | 依据 |
|----|--------|--------|------|
| CMake 最低版本 | — | **3.28** | `cmake/CMakeLists.txt:6` |
| C++ 标准 | 17 | **20**（低于即 `FATAL_ERROR`） | `cmake/onnxruntime_language_standard_versions.cmake:9`（常量）、`:48-65`（强制逻辑） |
| 顶层 CMakeLists | 无 | **仍无**——`cmake/` 是唯一入口 | `ls CMakeLists.txt` 不存在 |

设备侧 CMake 为 SDK 自带 3.28，满足最低要求。

### 1.2 `MINIMAL_BUILD` 的连带效应（重要，本版本明确关闭）

1.29.1 把原来 `if(onnxruntime_MINIMAL_BUILD)` 的配置块换成了
`cmake_dependent_option`（`cmake/CMakeLists.txt:114-116, 200, 202, 207-208`）：

```cmake
cmake_dependent_option(onnxruntime_DISABLE_RTTI  ... ON "NOT onnxruntime_ENABLE_PYTHON;NOT onnxruntime_USE_CUDA" OFF)
cmake_dependent_option(onnxruntime_DISABLE_EXCEPTIONS ... ON "onnxruntime_MINIMAL_BUILD;NOT onnxruntime_ENABLE_PYTHON" OFF)
```

即 `MINIMAL_BUILD=ON` 会**静默**把 `DISABLE_EXCEPTIONS` 与 `DISABLE_RTTI` 打开，
等于把正常运行时能力砍掉一截。本配方因此：

```
-Donnxruntime_MINIMAL_BUILD=OFF
-Donnxruntime_DISABLE_EXCEPTIONS=OFF
-Donnxruntime_DISABLE_RTTI=OFF
```

全算子集，不做"假 PASS"式的缩减。

### 1.3 宿主工具：protoc 仍然必须由构建主机提供

`cmake/external/protobuf_function.cmake:40-45`：

```cmake
if(EXISTS ${ONNX_CUSTOM_PROTOC_EXECUTABLE})   # 用外部宿主 protoc
else() $<TARGET_FILE:protobuf::protoc>        # 否则用刚构建的目标 protoc
```

交叉编译下后者是 aarch64 二进制，在构建主机上无法执行。
1.29.1 新增了 `CMAKE_CROSSCOMPILING` 时 FetchContent 预编译 protoc 的分支
（`onnxruntime_external_deps.cmake:114-172`，版本见 `deps.txt:44-49`，均为
protobuf v21.12），但那需要构建期网络。

**本配方的做法（沿用 1.27.1 的离线安全路线）**：从镜像中的 protobuf v21.12
源码用宿主 clang 现场构建 `protoc`，再通过
`-DONNX_CUSTOM_PROTOC_EXECUTABLE=<path>` 传给 CMake。

### 1.4 flatbuffers：必须显式关闭 flatc

`cmake/external/onnxruntime_external_deps.cmake:449-452` 只为
iOS / tvOS / visionOS / Android / Emscripten 自动设置
`FLATBUFFERS_BUILD_FLATC=OFF`——**OHOS 不在名单里**，不显式关闭就会把
aarch64 的 `flatc` 作为 ALL 依赖构建。

上游已提交生成好的 flatbuffer 头文件
（`onnxruntime/core/flatbuffers/schema/ort.fbs.h`、`ort_training_checkpoint.fbs.h`，
banner 显示由 flatc v23.5.26 生成，与 `deps.txt` 一致），因此不需要 flatc。

本配方：`-DFLATBUFFERS_BUILD_FLATC=OFF`，并通过补丁 0005 在 OHOS 上跳过
flatbuffers 的 FetchContent 补丁步骤（该步骤用 toybox 不支持的 patch 选项）。

### 1.5 cpuinfo：FetchContent 引入，必须 configure 后就地修补

上游只在 `CMAKE_SYSTEM_NAME STREQUAL "Linux"` 时套用 Linux sysfs 处理
（`onnxruntime_external_deps.cmake:378-397`），OHOS 落到裸 `else()`。
cpuinfo 来自 FetchContent，conandata 补丁够不到它，因此配方在 configure
之后改写 `_deps/pytorch_cpuinfo-src/CMakeLists.txt`，把 OHOS 并入 Linux 分支。

### 1.6 补丁的重新验证与重新生成

对 1.29.1 源码树逐个 `patch -p1 --dry-run` 实测：

| 补丁 | 1.29.1 应用结果 | 处置 |
|------|------------------|------|
| 0001 adjust_global_compile_flags | 干净应用 | 沿用 |
| 0002 onnxruntime_mlas | 干净应用 | 沿用 |
| 0003 external/abseil-cpp | **失败** | **重新生成** |
| 0004 external/eigen | 干净应用 | 沿用 |
| 0005 external/onnxruntime_external_deps | hunk 7 失败（dawn 段） | **重新生成** |
| 0006 external/xnnpack | 干净应用 | 沿用 |
| 0007 core/platform/posix/env.cc | 干净应用 | 沿用 |
| 0008 core/mlas/lib/mlasi.h | 干净应用 | 沿用 |

**0003 为何失败**：1.29.1 把 abseil 的 vcpkg 补丁路径从
`patches/abseil/*.patch` 改成 `vcpkg-ports/abseil/*.patch`，并且新增了
`absl_cuda13_member_template.patch`（调用列表由 2 条变 3 条）。旧补丁的上下文
不再匹配。重新生成的补丁在当前文件上做同样的 `-l -p1` 替换
（5 处），并保留新增的 cuda13 补丁调用。

**0005 为何失败**：dawn 段在 1.29.1 中新增了
`dawn_parallel_build_fix.patch` 等调用，hunk 7 的上下文整体位移。重新生成后
覆盖全部 16 处 `--binary --ignore-whitespace -p1` → `-l -p1`，并保留
flatbuffers 的 OHOS 跳过逻辑。

两个重新生成的补丁都已在纯净副本上复验：
`patch -p1 --dry-run` → **APPLIES CLEAN**。

### 1.7 其它

- `onnxruntime_USE_PREINSTALLED_EIGEN` 是**死选项**（全树仅其自身声明一处），
  Eigen 始终经 FetchContent 获取（`cmake/external/eigen.cmake:10-17`）。
- 缺失/改名选项核对：`onnxruntime_USE_ROCM`、`onnxruntime_USE_MLAS`、
  `onnxruntime_USE_EIGEN_FOR_BLAS`、`onnxruntime_USE_ARMNN`、
  `onnxruntime_USE_PREINSTALLED_PROTOBUF`、`onnxruntime_USE_FLATBUFFERS`、
  `onnxruntime_USE_ABSEIL`、`onnxruntime_USE_RE2`、`onnxruntime_USE_NSYNC`、
  `onnxruntime_USE_MPI`——**1.29.1 中均不存在**；本配方未设置这些（1.27.1
  配方同样未设置，故无影响）。
- `onnxruntime_BUILD_WEBASSEMBLY` 改名为 `onnxruntime_BUILD_WEBASSEMBLY_STATIC_LIB`
  （`cmake/CMakeLists.txt:235`）——本配方两者都不设置。

## 2. 依赖处理（镜像预下载，零构建期网络）

`cmake/deps.txt` 仍是 `Name;Url;SHA1` 的 CSV（1.29.1 共 72 行），
1.27.1 的解析器与镜像重写机制可直接沿用。关键版本：

| 依赖 | 版本 |
|------|------|
| protobuf | v21.12 |
| onnx | v1.22.0 |
| eigen | 1d8b82b0… |
| re2 | 2024-07-02 |
| flatbuffers | v23.5.26 |
| googletest | v1.17.0（仅测试用） |
| pytorch_cpuinfo | 4628dc06… |
| abseil-cpp | 20250814.0 |
| date | v3.0.1 |
| safeint / microsoft_gsl / json / mp11 | 3.0.28 / v4.2.1 / v3.11.3 / boost-1.82.0 |

配方把这 12 个依赖预下载到源码树下的 `mirror/`，并通过
`-Donnxruntime_CMAKE_DEPS_MIRROR_DIR=` 让上游把 `https://` URL 重写到该目录。

## 3. 构建配置

```
-DCMAKE_TOOLCHAIN_FILE=<OHOS SDK>/ohos/native/build/cmake/ohos.toolchain.cmake
-DOHOS_ARCH=arm64-v8a
-DCMAKE_CXX_STANDARD=20
-Donnxruntime_BUILD_SHARED_LIB=ON
-Donnxruntime_BUILD_UNIT_TESTS=OFF
-Donnxruntime_ENABLE_PYTHON=OFF
-Donnxruntime_MINIMAL_BUILD=OFF
-Donnxruntime_DISABLE_EXCEPTIONS=OFF
-Donnxruntime_DISABLE_RTTI=OFF
-Donnxruntime_DISABLE_CONTRIB_OPS=OFF
-Donnxruntime_USE_NNAPI_BUILTIN=OFF
-Donnxruntime_BUILD_JAVA=OFF -Donnxruntime_BUILD_CSHARP=OFF -Donnxruntime_BUILD_OBJC=OFF
-DFLATBUFFERS_BUILD_FLATC=OFF
-DONNX_CUSTOM_PROTOC_EXECUTABLE=<host protoc>
-Donnxruntime_CMAKE_DEPS_MIRROR_DIR=<source>/mirror
```

### Execution Provider 清单（第一阶段：CPU only）

关闭的 EP：CUDA、TensorRT、ROCm（选项已不存在）、DirectML、CoreML、NNAPI、
QNN、OpenVINO、ACL、DNNL、MIGRAPHX、VITISAI、RKNPU、XNNPACK（未启用）。
**未使用 MINIMAL_BUILD**——完整算子集与正常异常/RTTI 行为均保留。

## 4. 测试：诚实申报

### 4.1 上游测试（未运行，如实申报）

| 项 | 值 |
|----|----|
| 框架 | gtest（**FetchContent 下载**：`deps.txt:29` googletest v1.17.0） |
| 规模 | `onnxruntime/test/**/*_test.cc` 共 **453** 个 |
| 目标 | `onnxruntime_test_all`、`onnx_test_runner`、`onnxruntime_provider_test`、`onnxruntime_mlas_test` 等（`cmake/onnxruntime_unittests.cmake`，仅当 `onnxruntime_BUILD_UNIT_TESTS=ON` 时 include） |
| 本次执行 | **未执行（NOT_RUN）** |

未执行的技术原因：

1. 启用 `onnxruntime_BUILD_UNIT_TESTS` 会触发 googletest 的 FetchContent
   下载（构建期网络依赖，本仓库规则禁止；同 §2 的镜像机制虽可用，但需要
   额外把 googletest 纳入预下载清单并验证）。
2. 453 个测试文件在 farm 的单线程构建约束（`tools.build:jobs=1` +
   `CMAKE_BUILD_PARALLEL_LEVEL=1`）属下不可行量级。
3. 测试二进制为 aarch64，只能在 OHOS 设备上运行；本次未安排
   "构建→传输→设备侧运行" 流程。

如实申报 NOT_RUN，不把未运行的测试计为 PASS。

### 4.2 test_package（已执行，消费者视角）

`test_package/test_onnxruntime.cpp` 通过 **C API** 真实调用运行时，9 组断言：

| # | 动作 | 断言 |
|---|------|------|
| 1 | `OrtGetApiBase()` | 非空（运行时库加载成功） |
| 2 | `api_base->GetVersionString()` | 非空 |
| 3 | `api_base->GetApi(ORT_API_VERSION)` | 非空 |
| 4 | `api->CreateEnv(ORT_LOGGING_LEVEL_WARNING, ...)` | 成功且 env 非空 |
| 5 | `api->CreateSessionOptions(&opts)` | 成功且 opts 非空 |
| 6 | `api->SetIntraOpNumThreads(opts, 1)` | 成功 |
| 7 | `api->SetSessionGraphOptimizationLevel(opts, ORT_ENABLE_BASIC)` | 成功 |
| 8 | `api->CreateRunOptions(&run_opts)` | 成功 |
| 9 | `api->GetAvailableProviders()` | 成功且 provider 数 > 0（证明完整运行时的 EP 注册表已链接进库，而不是被裁剪过的构建） |
| 10 | 逆序释放 run_opts / session_options / env | 正常返回，无崩溃 |

测试二进制为 aarch64，在 OHOS PC 上原生运行。

## 5. 产物

`lib/libonnxruntime.so`、`include/onnxruntime/**`（C/C++ API 头）。
CMake 包配置以 `onnxruntime::onnxruntime` 目标形态由 Conan CMakeDeps 提供。

## 6. 参考

- 上一版本配方：`archives/o/onnxruntime/1.27.1/`（作为演进基线）
- 上游：https://onnxruntime.ai
