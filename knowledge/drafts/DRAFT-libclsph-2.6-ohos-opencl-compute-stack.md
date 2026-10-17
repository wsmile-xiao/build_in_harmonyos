# DRAFT: OHOS PC 无 GPU OpenCL 计算栈（ocl-icd + Khronos 头 + oclgrind 软件后端）

## 问题描述

libclsph 2.6 是 OpenCL 加速的 SPH 流体仿真库：CMake `find_package(OpenCL REQUIRED)`、
内核用 OpenCL C 编写、C++ 侧用内嵌 cl.hpp C++ 绑定。在 HarmonyOS PC（arm64）上适配时
遇到三层阻塞：

1. **无头无库**：系统无 `CL/cl.h`、`cl_platform.h`，无 `libOpenCL.so`；制品仓也无
   opencl 头包（ocl-icd/2.3.5 只含 `ocl_icd.h`）。`find_package(OpenCL)` 直接失败。
2. **内嵌绑定残缺**：上游自带 2015 版 `util/cl.hpp`，缺 OpenCL 1.2 的
   `enqueueFillBuffer`；且上游调用形态是 `enqueueFillBuffer(buffer, pattern, 0, size)`
   ——pattern 按值传、省略 offset，标准签名（void* pattern, pattern_size, offset, size）
   无法直接匹配。
3. **内核不可移植**：`collisions.cl` 用 double 字面量 `0.001` 乘 float3，在严格 OpenCL
   实现（oclgrind/LLVM 后端）报 "scalar operand type has greater rank" 秩错误；
   真实 GPU 驱动隐式转换容忍，软件实现不容忍。

## 根因

- OHOS PC 无 GPU OpenCL 驱动且无系统 OpenCL 开发文件，属平台缺口而非库缺陷
- 老库（2016 年停更）内嵌的 C++ 绑定与内核按"真实 GPU 宽松语义"编写，对严格/软件
  OpenCL 实现不可移植

## 解决方案

1. **ICD loader**：配方 `requires("ocl-icd/2.3.5")` 提供 `libOpenCL.so`（构建链接 + 运行查找）。
2. **官方 CL 头**：conandata 第二来源固定官方 Khronos OpenCL-Headers（sha256 校验），
   `OPENCL_INCLUDE_DIRS` 指向它；`OPENCL_LIBRARIES` 指向 ocl-icd 包内 `libOpenCL.so*`。
3. **绑定修复**：`-DUSE_LOCAL_CL_HPP` 走内嵌 `util/cl.hpp`，补 `enqueueFillBuffer`：
   - 标准 C API 包装（buffer, pattern, pattern_size, offset, size）
   - 模板重载 `enqueueFillBuffer(buffer, const T& pattern, offset, size)` 匹配上游
     "pattern 按值" 调用 → 内部 `&pattern + sizeof(T) + offset`
4. **内核修复**：`0.001` → `0.001f`（float 字面量）。
5. **软件后端**：运行/测试无 GPU，用 oclgrind 软件 OpenCL 作平台提供方：
   `OCL_ICD_VENDORS=<目录>`（目录内含写有 `liboclgrind-rt-icd.so` 绝对路径的 .icd 文件）；
   test_package 以 test-only 依赖引入 oclgrind/26.03.1，conanrun env + cwd 数据目录运行。
6. **包内安装 CL 头**：`include/CL/*.h` 随包安装——消费方编译库的公开头（含 cl.hpp
   `#include <CL/opencl.h>`）需要它们。

## 验证

- `libclsph.a` 构建成功；打包 SPH 内核（grid/sort/sph/advection/collision/forces）在
  OHOS 上编译通过（Oclgrind Simulator 平台）
- 鸿蒙专项测试：平台枚举 → 内核编译 → 有界内核执行读回校验（1,4,9,16）PASS
- 上游示例 `clsphparticles` 推进仿真帧（oclgrind 软件渲染）
- 消费者验证：`CONSUMER PASS`（scene 10 faces/24 verts、settings 解析、
  initial_volume=1.60274 与期望值一致）
- conan-verify G2/G3/G4 PASS；test_package 双测试 rc=0

## 适用边界

- 适用于所有 `find_package(OpenCL)` 的三方库在无 GPU OpenCL 的 OHOS PC（arm64）上的适配
- 适用于自带内嵌 cl.hpp 绑定（USE_LOCAL_CL_HPP 模式）的老库
- 反例：有 GPU OpenCL 驱动的设备/需要真实硬件性能的库，不应引入软件后端（性能差异极大）
- 未覆盖：OpenGL/GLEW/GLFW 类图形栈（无对应软件平台时按各自门禁处理，libclsph 的
  opengl 示例即因 GLFW 缺失未实例化）

## 关联

- `similar_to`：E540（zlib shadow-ci 路径问题，同为 OHOS 工具链/运行时路径族）
- `prerequisite_of`：后续 OHOS 上 OpenCL 类库适配
- 无 `conflicts_with`
