# level-zero-gpu-raytracing 1.2.3 适配笔记

## 编译环境

- 构建系统: cmake (Ninja generator)
- 编译日期: 2026-09-26
- 编译器: clang / clang++ 15.0.4 (OHOS SDK)
- 目标平台: HarmonyOS PC, aarch64 (原生构建, build = target)
- 状态: built

## 上游与源码

| 项 | 值 |
|----|-----|
| 仓库 | https://github.com/intel/level-zero-raytracing-support |
| 版本 | v1.2.3 (tag) |
| 源码 URL | https://github.com/intel/level-zero-raytracing-support/archive/refs/tags/v1.2.3.tar.gz |
| SHA256 | `0bfb03903154228cdba0320e3bc09c57787558b368da315b9b32e9603198b5b3` |
| 许可证 | Apache-2.0 (LICENSE.txt) |
| 打包名对照 | Debian/Ubuntu 源码包名即 `level-zero-gpu-raytracing`，二进制包 `libze-intel-gpu-raytracing` |

SHA256 与 Debian `level-zero-gpu-raytracing_1.2.3.orig.tar.gz` 的官方校验和一致（双重印证来源可信）。

## 库的定位

该库实现 Level Zero 的 `ZE_extension_rtas` 扩展：在 CPU 侧构造光线追踪加速结构 (RTAS)，
产物与 Intel GPU 的光追硬件兼容。**应用不直接链接本库**——Level Zero loader
(`libze_loader.so.1`) 在运行时按扩展能力加载它，应用通过 loader 调用 `ZE_extension_rtas`。
库内含 `rtbuild/` (CPU 侧 QBVH6 构建算法) 与 `level_zero/` (`ze_wrapper` 运行时动态解析 loader)。

## 编译配置

```
-DCMAKE_POLICY_VERSION_MINIMUM=3.5    # 上游声明 cmake_minimum_required(3.1.0)，CMake 4.x 拒绝
-DZE_RAYTRACING_TBB=normal            # 用制品仓 TBB，而非上游 FetchContent 克隆 oneTBB
-DZE_RAYTRACING_SYCL_TESTS=OFF         # 上游硬件测试需 DPC++ 编译器与 Xe 设备
```

依赖 (conan):

| 依赖 | 版本 | 用途 |
|------|------|------|
| tbb | 2023.0.0.1 | 线程后端 (`ZE_RAYTRACING_TBB=normal`)，算法层 `parallel_for`/`parallel_reduce` 与并行操作对象的 `tbb::task_group` |
| sse2neon | 1.9.1 | 头文件级 SSE2 API 仿真层，供 aarch64 上的向量代码路径使用 |

系统库: `dl` (ze_wrapper 用 dlopen/dlsym 解析 loader)、`pthread` (TBB)。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `immintrin.h:14:2: error: "This header is only meant to be used on x86 and x64 architecture"` | `rtbuild/sys/intrinsics.h` **无条件** `#include <immintrin.h>`；aarch64 上该头直接 `#error` | 补丁 0003：按架构守卫，x86 走 `<immintrin.h>`，其余走 SSE2 仿真头 |
| 2 | `fatal error: '../simd/arm/emulation.h' file not found` | `rtbuild/math/emath.h` 在 `__ARM_NEON` 分支引用了 `simd/arm/emulation.h`；该文件在 v1.2.3 源码包与上游 main **均不存在**（已用 GitHub git tree API 核实：273 个路径中无任何 arm/neon/emulation 文件） | 补丁 0002：改引 SSE2 仿真头（上游未发布的 ARM 源路径） |
| 3 | `error: call to 'min' is ambiguous`（`parallel_partition.h`） | `rtbuild/sys/platform.h` 只在 x86 定义 `__64BIT__`，导致 `emath.h` 中 `size_t min(size_t,size_t)` 重载缺失，`size_t` 实参只能匹配 `int`/`unsigned` 两个重载 | 补丁 0004：`__64BIT__` 检测加入 `__aarch64__` / `_M_ARM64` |
| 4 | `ld.lld: error: unable to find library -ltbb` | 上游 `rtbuild/CMakeLists.txt` 以裸库名 `tbb` 链接；由包管理器提供的 TBB 只暴露 imported target，不保证链接器搜索路径 | 补丁 0001：`IF (TARGET tbb::tbb)` 优先用 imported target，回退裸名 |
| 5 | `CMake Error: Compatibility with CMake < 3.5 has been removed` | 上游 `cmake_minimum_required(VERSION 3.1.0)`，本机 CMake 4.1.2 | 配方注入 `CMAKE_POLICY_VERSION_MINIMUM=3.5`（**不改源码**） |
| 6 | `Could not find a package configuration file provided by "TBB"`（`inject_headers` 模式） | 上游 `inject_headers` 仅注入自带头文件，随后仍无条件 `find_package(TBB)` 回退到 `pkg_check_modules(tbb)` | 改用 `ZE_RAYTRACING_TBB=normal`，由配方 `generate()` 的 `CMakeDeps` 生成 `TBBConfig.cmake` 供上游 `find_package(TBB)` 命中 |
| 7 | `fatal error: 'tbb/tbb.h' file not found` | `normal` 模式只 `find_package(TBB)` 拿 target，不注入头文件搜索路径 | 补丁 0001 让上游链接 `tbb::tbb` **imported target**，其 `INTERFACE_INCLUDE_DIRECTORIES` 自动携带 TBB include 路径，无需手工指定头文件目录 |

## 关于补丁的中立性

4 个补丁全部为**平台可移植性**修复，不含 `__OHOS__` 平台宏（符合 R8 / PF5 口径）：

- 0001：优先使用 imported target，`ELSE` 回退裸 `tbb`，**不破坏**上游原有链接方式。
- 0002：`__ARM_NEON` 分支原本指向一个不存在的文件（该分支上游从未能编译），改为可用实现。
- 0003：以标准架构宏 `__x86_64__` / `__i386__` / `_M_X64` / `_M_IX86` 守卫。x86 上行为**逐字节不变**。
- 0004：`__64BIT__` 增加 `__aarch64__` / `_M_ARM64`——这正是该宏的本意（64 位平台检测）。x86 上行为不变。

## 上游测试清点（R51 申报）

上游测试位于 `testing/`，由 `ZE_RAYTRACING_SYCL_TESTS` 门控，**默认 OFF**。

| 清点项 | 数量 | 证据 |
|--------|------|------|
| `ADD_EXECUTABLE`（测试可执行文件） | 4 | `testing/CMakeLists.txt`：`rthwif_cornell_box`、`rthwif_test`、`rthwif_cornell_box_ext`、`rthwif_test_ext` |
| `ADD_INDIVIDUAL_TEST(...)`（ctest 用例注册） | 56 | 同上（其中 52 项同时注册 `G` 变体，15 项注册 `S32` 变体） |
| `-fsycl -fsycl-targets=spir64` 属性赋值 | 8 | 每个测试可执行文件的 `COMPILE_FLAGS` / `LINK_FLAGS` |
| 本平台实际可运行 | **0 / 56** | 见下 |

**不可运行的具体技术原因（逐项，非"没环境"）：**

1. **缺编译前端**：每个测试目标都强制 `-fsycl -fsycl-targets=spir64`，需要 Intel DPC++
   编译器（icpx）；OHOS SDK 的 clang 15 无 SYCL 支持，configure 阶段即无法构建测试目标。
2. **缺 GPU 硬件**：测试在 Cornell Box / 三角形 / 程序化几何上做 RTAS 构建并与
   `cornell_box_reference.tga` 逐像素比对，要求 Intel Xe 设备（Alchemist/Meteor Lake 等）
   与可用 `libze_loader` + 内核态驱动；OHOS PC 无 Intel Xe 设备，`zeInit` 无法取得设备。
3. **缺运行时依赖**：`testing/CMakeLists.txt` 还会安装 `libpi_level_zero.so`、`libur_loader.so`、
   `libumf.so`、`libsvml.so` 等来自 DPC++ 工具链的 SYCL 运行时，这些在 OHOS 侧不存在。

因此 MANIFEST.yml 中 `upstream_tests: []`、`upstream_test_in_build: false`，并将
`ZE_RAYTRACING_SYCL_TESTS` 保持上游默认值 `OFF`（与上游 Debian 打包 `rules` 一致）。

## 验证结果

配方已通过 `conan create` 全流程验证（含 `test_package` 真实调用）：

```bash
# 在 archives/l/level-zero-gpu-raytracing/1.2.3/ 下执行
conan create . \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
# → level-zero-gpu-raytracing/1.2.3: Package '9d809a365dd2b51f25d3bdafe845ea1ae8940edb' created
# → [100%] Built target test_level_zero_gpu_raytracing
# → ======== Testing the package: Executing test ========
# → === ALL CHECKS PASSED (failures=0) ===
# → exit code 0
```

其中 configure 关键参数由配方 `generate()` 注入（无需手工传参）：

| 参数 | 值 | 作用 |
|------|-----|------|
| `CMAKE_POLICY_VERSION_MINIMUM` | `3.5` | 兼容 CMake 4.x 对 `cmake_minimum_required(3.1.0)` 的拒绝 |
| `ZE_RAYTRACING_TBB` | `normal` | 用制品仓 TBB 而非上游 FetchContent 克隆 |
| `ZE_RAYTRACING_SYCL_TESTS` | `OFF` | 跳过需 DPC++/Xe 设备的硬件测试构建 |
| `CMAKE_CXX_FLAGS` / `CMAKE_C_FLAGS` | `-I<sse2neon 包>/include` | 提供 aarch64 上的 SSE2 API |

构建产物（`ninja` 顺序）：`libsys.a` → `libsimd.a` → `libze_intel_gpu_raytracing.so` → `libze_wrapper.a`（11/11 目标全绿）。

产物：

| 文件 | 说明 |
|------|------|
| `lib/libze_intel_gpu_raytracing.so` | 主库（`export.linux.map` 版本脚本导出 `ze*` 符号） |
| `include/rtbuild.h` | 公开 API 头（上游 install 不装头文件，本配方补齐） |
| `include/level_zero/{ze_api.h,ze_wrapper.h,ze_api_exp_ext.h}` | `rtbuild.h` 的传递包含 |

消费者测试（test_package）实测调用结果：

| 调用 | 返回值 |
|------|--------|
| `zeRTASBuilderCreateExtImpl(nullptr, desc, &b)` | `0x78000005` `ZE_RESULT_ERROR_INVALID_NULL_HANDLE` |
| `zeRTASBuilderCreateExtImpl(fakeDriver, desc, &b)` | `0x00000000` `ZE_RESULT_SUCCESS`（builder 非空） |
| `zeRTASBuilderDestroyExtImpl(builder)` | `0x00000000` `ZE_RESULT_SUCCESS` |
| `zeDriverRTASFormatCompatibilityCheckExtImpl(drv, 1, 1)` | `0x00000000` `ZE_RESULT_SUCCESS` |
| `zeDriverRTASFormatCompatibilityCheckExtImpl(drv, 1, 2)` | `0x7ff00004` `ZE_RESULT_EXP_ERROR_OPERANDS_INCOMPATIBLE` |
| `zeDriverRTASFormatCompatibilityCheckExtImpl(drv, INVALID, INVALID)` | `0x7800000c` `ZE_RESULT_ERROR_INVALID_ENUMERATION` |
| `zeDriverRTASFormatCompatibilityCheckExtImpl(nullptr, 1, 1)` | `0x78000005` `ZE_RESULT_ERROR_INVALID_NULL_HANDLE` |

这些返回值两两互斥且各不相同，证明校验/比较逻辑真实执行；未链接本库时符号无法解析
（测试亦以 `dlsym` 断言 4 个导出符号存在于动态符号表），L1e 破坏性反向验证天然成立。

## 依赖版本

- tbb/2023.0.0.1（制品仓）
- sse2neon/1.9.1（制品仓）

## 注意事项

- **R40 深度适配完整性**：本库属"图形渲染 / 系统底层"类。本环境**无 Intel Xe GPU 与 L0 驱动**，
  因此硬件路径（真实 RTAS 构建、与光追硬件兼容性）**无法在本平台验证**。已验证的是：
  库可构建、可加载、导出符号完整、API 校验与格式比较逻辑行为正确。硬件功能验证需在具备
  Intel Xe 设备 + Level Zero 驱动的环境中进行。
- `ze_wrapper` 以 `dlopen("libze_loader.so.1")` 在运行时解析 loader，因此**运行期**需要
  Level Zero loader 存在；库本身加载不依赖 loader（dlopen 失败延后到实际调用）。
- 上游 install 规则不含头文件，本配方在 `package()` 中补齐 `rtbuild.h` 与 `level_zero/*.h`。
---

**编译结束**: 2026-09-26 23:11
**最终状态**: built
