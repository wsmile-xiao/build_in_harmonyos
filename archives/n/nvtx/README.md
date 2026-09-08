# NVTX

NVIDIA Tools Extension — C/C++ 性能分析与调试标注库（官方 C/C++ API 发布版）。

## 功能概述

- NVTX C API（`nvtx3-c`）：事件/范围标注、线程命名、计数器、payload 扩展（`nvToolsExt.h` 等）
- NVTX C++ API（`nvtx3-cpp`）：RAII `nvtx3::scoped_range`、`nvtx3::mark`、`nvtx3::domain` 等
- NVTXW Writer API（`nvtxw3-loader` 静态库）：`nvtxwLoad`/`nvtxwUnload` 后端加载器（dlopen/dlsym）

## OHOS 适配

- 构建：CMake（`cmake_minimum_required 3.19`），`NVTX3_INSTALL=ON`
- 目标：`nvtx3-c`（INTERFACE 头文件）、`nvtx3-cpp`（INTERFACE 头文件）、`nvtxw3-loader`（STATIC，唯一编译单元 `src/nvtxw3_loader.c`）
- 依赖：无第三方包；`nvtx3-c` 仅链接 `${CMAKE_DL_LIBS}`（dl）
- 包内导出：`nvtx3::nvtx3-c` / `nvtx3::nvtx3-cpp` / `nvtx3::nvtxw3-loader`（find_package(nvtx3)）
- 验收：`test_package` 消费者测试（scoped_range/mark + nvtxNameOsThreadA + loader 缺失后端优雅返回）
- 上游测试：106/106 ctest 注册项通过（ENABLE_CUDA=OFF 配置，详见最终回报台账）