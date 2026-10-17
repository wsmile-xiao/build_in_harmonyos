- **三方库名称**：vkfft（VkFFT —— GPU 加速 FFT 头文件库，Vulkan/CUDA/HIP/OpenCL 多后端，本包覆盖上游默认的 Vulkan 后端）
- **上游版本**：v1.3.4
- **上游仓库地址**：https://github.com/DTolm/VkFFT
- **适配路径**：路径 A（基础适配）
- **使用知识库**：无（本次沉淀新草稿 knowledge/drafts/DRAFT-vkfft-1.3.4-build-scripts-dep-visible-false.kv：package_type=build-scripts 的依赖被 Conan 2.29 自动 visible=False，下游 cpp_info.requires 校验报 not a direct requirement，须 self.requires(..., visible=True) 显式恢复）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游无 ctest/make check 测试框架 |
| 集成测试 | 0 | 同上 |
| 其他测试 | 30 | 来源：根目录 VkFFT_TestSuite 可执行（CMakeLists.txt 注册 30 个 VkFFT sample 源：11 benchmark + 9 precision + 3 convolution + 7 批量 benchmark），运行时需 Vulkan GPU 设备 + glslang 做 SPIR-V shader 编译 |
| **合计** | **30** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游本无 |
| 集成测试 | 0 | 不变 | 上游本无 |
| 鸿蒙特有测试 | 1 | 新增 | test_package/test_vkfft.cpp 消费者用例：VKFFT_BACKEND=0 包含 <vkFFT/vkFFT.h>（透传 vulkan/vulkan.h 与 glslang C 接口），构造 VkFFTConfiguration 真实 1D FFT 计划描述并校验字段，编译+链接+运行全链路在 OHOS aarch64 (clang 15, libc++, cppstd=17) 完成，共 3 断言 |
| **合计** | **1** | **+1** | 3/3 断言通过 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖（VkFFT_TestSuite，30 sample）
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> 说明：上游测试用例本身存在（30 个 sample），本包新增的 1 个消费者用例
> （test_package/test_vkfft.cpp）属鸿蒙平台消费者端验证（计鸿蒙特有测试 +1），
> 非对上游测试缺口的补全。

## 验证结果

- 编译状态：通过（conan create 全链路 rc=0；conan-verify G0–G4 + L2/L4/L5 全绿；W3 本地 CI exit_code=0，.ci-result.json integrity_hash=9afe169bfa5efb81；W4 独立审计 verdict=pass，P0=0 P1=0）
- 上游测试用例通过率：0/30（0%）—— **平台限制披露（R51 逐项原因）**：全部 30 个 sample 运行时需 ①Vulkan GPU 设备（vkCreateInstance/队列/命令缓冲真实 FFT）；②glslang 运行时（GPU 侧 SPIR-V 编译）；③构建期 FetchContent 在线拉取 glslang 12.3.1。CI worker 为无 GPU 容器环境，三条均无法满足；唯一可行运行途径是带 Vulkan GPU 的鸿蒙 PC 真机，属平台能力边界而非适配缺陷。
- 新增测试用例通过率：1/1（100%，3/3 断言；`vkFFT 1.3.4 consumer OK: sizeof(VkFFTApplication)=2720 sizeof(VkFFTConfiguration)=1216 FFTdim=1 size0=64 batches=1`）

## 补充说明

- **包形态**：vkfft 为 header-only 库（`package_type = "header-library"`），打包上游 `vkFFT/` 完整头树为 `include/vkFFT/`；`cpp_info.includedirs` 同时挂 `include/` 与 `include/vkFFT/` 双根（内部头 `#include "vkFFT/vkFFT_Structs/..."` 以内层 vkFFT 目录的父目录为根解析，与上游给 benchmark 加两个 -I 等价）。
- **glslang 平铺 shim**：vkFFT.h 顶层平铺 `#include "glslang_c_interface.h"`（上游以 `-I glslang/glslang/Include/` 实现）；ohpcd 的 glslang/vulkan-sdk-1.3.290.0 制品将该头装在 `glslang/Include/` 子目录，为不改上游源码，包内 include 根放转发 shim 头。
- **依赖**（均已发布制品仓，R36 通过）：vulkan-headers/vulkan-sdk-1.4.357.0、glslang/vulkan-sdk-1.3.290.0。
- **已知限制**：本包仅覆盖 Vulkan 后端（VKFFT_BACKEND=0，上游默认）；CUDA/HIP/OpenCL 等后端需对应 GPU 工具链，不在本包范围。消费者执行真机 GPU FFT 还需设备侧 Vulkan loader/驱动；本包保证头文件编译期可用性与 glslang 静态库链接能力。
- 无源码补丁（patches_applied=0）；MIT 许可证已随包导出。
