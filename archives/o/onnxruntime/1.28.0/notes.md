# ONNX Runtime 1.28.0 — 鸿蒙适配笔记

## 基本信息
- 软件名称: onnxruntime
- 版本: 1.28.0
- 构建系统: CMake (cmake/CMakeLists.txt)
- 上游仓库: https://github.com/microsoft/onnxruntime
- 许可证: MIT
- 目标平台: OHOS aarch64 (arm64-v8a)

## 构建配置
- onnxruntime_BUILD_SHARED_LIB=ON (动态库)
- onnxruntime_MINIMAL_BUILD=ON (最小化构建，支持 ORT 格式模型)
- onnxruntime_BUILD_UNIT_TESTS=OFF
- onnxruntime_ENABLE_PYTHON=OFF
- onnxruntime_DISABLE_CONTRIB_OPS=OFF
- onnxruntime_USE_NNAPI_BUILTIN=OFF

## 源码修改 (7处)

### 1. patch 命令选项适配
- 文件: cmake/external/abseil-cpp.cmake, eigen.cmake, onnxruntime_external_deps.cmake, xnnpack.cmake
- 原因: OHOS 的 patch 命令 (toybox 0.8.12) 不支持 `--binary` 和 `--ignore-whitespace` 选项
- 修复: 将 `--binary --ignore-whitespace` 替换为 `-l` (loose match)

### 2. flatbuffers patch 跳过
- 文件: cmake/external/onnxruntime_external_deps.cmake
- 原因: flatbuffers patch 的 hunk 1 在 OHOS 上不匹配 (toybox patch 不支持部分应用)
- 修复: 添加 `NOT CMAKE_SYSTEM_NAME STREQUAL "OHOS"` 条件，跳过 flatbuffers patch
- 影响: patch 内容是 GCC 警告修复和 AIX 适配，OHOS 不需要

### 3. OHOS 编译选项
- 文件: cmake/adjust_global_compile_flags.cmake
- 修复: 添加 `add_compile_options(-march=armv8.2-a+bf16+fp16)` 和 `-Wno-unused-command-line-argument`
- 原因: OHOS 工具链的 `--gcc-toolchain` 标志触发 unused 警告; BF16/FP16 指令集需要显式启用

### 4. MLAS target 编译选项
- 文件: cmake/onnxruntime_mlas.cmake
- 修复: 添加 `target_compile_options(onnxruntime_mlas PRIVATE -march=armv8.2-a+bf16+fp16)`
- 原因: MLAS 库的源文件需要 BF16 指令集支持

### 5. bfloat16_t 条件编译守卫
- 文件: onnxruntime/core/mlas/lib/mlasi.h
- 修复: 将 `#if defined(__aarch64__) && defined(__linux__)` 改为 `&& defined(__ARM_FEATURE_BF16)`
- 原因: 有自定义 `-march` 的 MLAS 文件 (如 dotprod, i8mm) 不包含 bf16 扩展，导致 bfloat16_t 未知

### 6. pthread_setaffinity_np musl 适配
- 文件: onnxruntime/core/platform/posix/env.cc
- 修复: 添加 `&& !defined(__MUSL__)` 到线程亲和性设置的条件编译守卫
- 原因: OHOS 使用 musl libc，不支持 `pthread_setaffinity_np` GNU 扩展

### 7. cpuinfo 平台检测
- 文件: pytorch_cpuinfo/CMakeLists.txt (FetchContent 提取后)
- 修复: 将 `CMAKE_SYSTEM_NAME STREQUAL "Linux"` 扩展为包含 `"OHOS"`
- 原因: cpuinfo 库不认识 OHOS 平台，未编译 ARM Linux 初始化代码
- 处理方式: 在 conanfile.py 的 build() 中，CMake configure 后自动 patch

### 8. ONNX 1.22.0 tensor.h 异常兼容（1.28.0 新增）
- 文件: onnx/common/tensor.h (FetchContent 提取后, ONNX 1.22.0)
- 修复: 将两处 `throw tensor_error(msg)` 改为 `ONNX_THROW_EX(tensor_error(msg))`
- 原因: ONNX 1.22.0 新增 safe_dim_product()，elem_num()/size_from_dim() 使用原生 throw；
  ORT 以 -fno-exceptions 编译第三方依赖并定义 ONNX_NO_EXCEPTIONS，throw 编译失败
  （"cannot use 'throw' with exceptions disabled"）。ONNX_THROW_EX 在
  ONNX_NO_EXCEPTIONS 下 abort()，否则保持 tensor_error 语义。
- 处理方式: 在 conanfile.py 的 build() 中，CMake configure 后自动 patch（与 cpuinfo 同模式）

## 特殊构建步骤
1. **预下载 FetchContent 依赖**: 12个依赖包下载到 mirror/ 目录，避免网络问题
2. **预构建 protoc**: 从 protobuf 源码单独编译 protoc 二进制 (交叉编译需要)
3. **OHOS NDK 工具链**: 使用 ohos.toolchain.cmake，设置 CMAKE_SYSTEM_NAME=OHOS
4. **AR/RANLIB 路径**: 手动指定 `/data/service/hnp/bin/llvm-ar` 和 `llvm-ranlib` (NDK 目录中不存在)

## 版本升级说明（1.27.1 → 1.28.0）

- 上游变化：ONNX 1.21.0→1.22.0、cpuinfo 换 commit（集成 cpuinfo_deinitialize）、abseil patch 路径迁移至 vcpkg-ports/abseil/（新增 cuda13 patch）、duktape（WGSL 动态生成器）移除、MLAS 新增 ARM64 2-bit 权重与 RISC-V RVV 内核。abseil/eigen/flatbuffers/protobuf 依赖版本要求与 1.27.1 完全相同。
- 补丁迁移：0001/0002/0004/0006/0007/0008 直接适用（git apply --check 通过，原样沿用）；0003/0005 因 abseil patch 路径变更和 duktape 移除导致 hunk 偏移，按 1.28.0 上下文重定位重写（修改语义不变：`--binary --ignore-whitespace` → `-l`，flatbuffers patch OHOS 跳过）。
- sha256 双源核对：Homebrew homebrew-core 59a955a15ddb（v1.28.0 公式）与本地镜像下载计算一致。
- 黄金验证：干净树应用全部 8 补丁后与 .work 树 diff=0。

## 依赖管理
ONNX Runtime 使用 CMake FetchContent 自管理依赖，conanfile.py 不需要 self.requires()。
核心依赖: abseil-cpp, protobuf, ONNX 1.22.0, re2, flatbuffers, safeint, GSL, date, eigen, cpuinfo, mp11, json

## 构建产物
- libonnxruntime.so.1.28.0 (8.4MB, ELF 64-bit arm64)
- 公共头文件 (onnxruntime_c_api.h 等)
- pkg-config 文件
- CMake 配置文件
---

**编译结束**: 2026-09-12 (见学习日志 learninglog/20260912onnxruntime-1.28.0/)
**最终状态**: built
