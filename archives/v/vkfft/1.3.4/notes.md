# vkfft 1.3.4 适配笔记

## 上游身份判定（动手前三证互证）

- 上游仓库: https://github.com/DTolm/VkFFT（Khronos 生态知名 GPU FFT 库，作者 DTolm）
- 发布包命名: tag `v1.3.4` → `VkFFT-1.3.4.tar.gz`（下载实测 6,135,651 字节）
- 主要语言: C/C++ 头文件库（vkFFT.h + vkFFT/ 子树），lang-preflight 判定 cpp 99%
- 许可证: MIT

## 编译环境

- 构建系统: conan（header-library，上游 CMake 仅用于构建 TestSuite 可执行，不打包）
- 编译日期: 2026-10-09
- 编译器: clang 15.0.4（--target=aarch64-linux-ohos -fuse-ld=lld）
- 状态: built

## 适配要点

vkFFT 是头文件库，本配方按 `package_type = "header-library"` 打包 Vulkan 后端
（VKFFT_BACKEND=0，上游默认）的完整头文件树：

1. **包布局**：上游 `vkFFT/` 目录整体拷贝为 `include/vkFFT/`，保持消费者
   `#include <vkFFT/vkFFT.h>` 与上游一致；`cpp_info.includedirs` 同时挂
   `include/` 与 `include/vkFFT/` —— 内部头（如 vkFFT_RunApp.h）用
   `#include "vkFFT/vkFFT_Structs/..."` 引用兄弟目录，需要内层 `vkFFT/`
   目录的父目录在 include path 上（与上游给 benchmark 加两个 -I 等价）。
2. **glslang 平铺 shim**：vkFFT.h 顶层 `#include "glslang_c_interface.h"`，
   上游通过 `-I glslang-main/glslang/Include/` 实现平铺；ohpcd 的
   glslang/vulkan-sdk-1.3.290.0 制品把该头装在 `glslang/Include/` 子目录。
   为不改上游源码，包内 include/ 根放转发 shim 头
   `glslang_c_interface.h → #include <glslang/Include/glslang_c_interface.h>`。
3. **依赖**（均已发布 ohpcd，R36 通过）：
   - vulkan-headers/vulkan-sdk-1.4.357.0（vulkan/vulkan.h 类型）
   - glslang/vulkan-sdk-1.3.290.0（glslang_c_interface.h + 运行时 SPIR-V 编译）

## 上游测试清点与运行情况（R51 三步法）

- 清点：上游无 ctest/make check 框架；唯一测试载体为根目录
  `VkFFT_TestSuite` 可执行（CMakeLists.txt 注册 30 个 VkFFT sample 源：
  11 个 benchmark + 9 个 precision + 3 个 convolution + 7 个批量 benchmark）。
- 运行：**已于 2026-10-11 在鸿蒙 PC 真机（Maleoon 916，Vulkan 1.2.275）
  全量真实执行 30/30 sample，通过 16 个**；其余 14 个均为执行后的设备级结果
  （10 个 fp64 能力缺失：设备 shaderFloat64=0；1 个显存不足；3 个全尺寸扫描
  benchmark 超 900 s 限时）。构建禁用上游 FetchContent，glslang 改链制品仓
  同源静态库；逐项明细与全量日志见 reports/test-report.md §二 与
  reports/vkfft-testsuite-run/。CI worker 仍无 GPU，CI 侧维持编译级验证。
- 替代验证：test_package 以 VKFFT_BACKEND=0 完整包含 vkFFT.h（透传
  vulkan/vulkan.h + glslang C 接口），构造 VkFFTConfiguration 真实 1D FFT
  计划描述并校验字段，编译+链接+运行全链路在 OHOS aarch64 工具链下通过。

## 编译步骤（验证命令）

```bash
# 手工探针（先于 conan create 验证包含链）
clang++ --target=aarch64-linux-ohos -fuse-ld=lld -std=c++17 \
  -I<glslang-include> -I<vulkan-include> \
  -I<stage>/include -I<stage>/include/vkFFT probe.cpp -o probe && ./probe
# → vkFFT consumer OK: sizeof(VkFFTApplication)=2720 sizeof(VkFFTConfiguration)=1216

# 正式验证
ohc-run.py conan-verify vkfft 1.3.4   # conan create + test_package
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `'glslang_c_interface.h' file not found` | glslang 制品把该头装在 glslang/Include/ 子目录，vkFFT.h 平铺 include | 包内放转发 shim 头（不改上游源码） |
| 2 | `'vkFFT/vkFFT_Structs/vkFFT_Structs.h' file not found` | 内部头引用需以内层 vkFFT/ 的父目录为 include 根 | cpp_info.includedirs 挂 include/ + include/vkFFT/ 双根 |
| 3 | 上游 CMake 无法直接用于打包 | TestSuite 需 FetchContent 在线拉 glslang + Vulkan GPU | 头文件库直接 shutil 打包，不做 CMake 构建 |

## 验证结果

- 手工探针编译+运行：通过（aarch64 OHOS）
- conan create + test_package：见 .ci-result.json（W3 自动写入）

## 注意事项

- 消费者运行时若执行真机 FFT，还需设备上有 Vulkan loader/GPU 驱动；
  本包仅保证头文件编译期可用性与 glslang 静态库链接能力。
- 如需 CUDA/HIP/OpenCL 后端，须改用对应 VKFFT_BACKEND 并补相应依赖，
  当前配方仅覆盖 Vulkan 后端（上游默认）。
---

**编译结束**: 2026-10-09 21:04
**最终状态**: built
