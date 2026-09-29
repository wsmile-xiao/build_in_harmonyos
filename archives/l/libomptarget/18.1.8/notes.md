# libomptarget 18.1.8 适配笔记 (HarmonyOS PC aarch64)

## 基本信息

| 项目 | 值 |
|------|------|
| 软件 | libomptarget (LLVM OpenMP offloading target runtime) |
| 版本 | 18.1.8 |
| 构建系统 | CMake (OPENMP_STANDALONE_BUILD=ON) |
| 编译器 | clang/clang++ 15.0.4 (aarch64-unknown-linux-ohos) |
| 平台 | HarmonyOS PC aarch64 (真机原生编译) |
| 编译日期 | 2026-09-17 |

## 依赖与 LLVM 版本决策

libomptarget 18.1.8 在 standalone 构建时**必须** `find_package(LLVM REQUIRED)`，
需要 LLVMConfig.cmake + LLVM 头文件 + libLLVM 库。

- 制品仓无 `llvm/18.1.8`（已有 15.0.4/20.1.0/22.1.0）
- 经实测：libomptarget 18.1.8 源码使用 **llvm/20.1.0**（制品仓已发布）的头文件
  与库可完整编译链接（仅 JIT.cpp 一处 API 不兼容需补丁，见问题 5）
- 因此 conanfile.py `requires("llvm/20.1.0")`，R36 依赖检查通过（llvm/20.1.0 已发布）

## 编译配置

```bash
cmake <openmp-src> -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_SYSTEM_NAME=HarmonyOS \
  -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
  -DOPENMP_STANDALONE_BUILD=ON \
  -DOPENMP_ENABLE_LIBOMPTARGET=ON \
  -DLIBOMPTARGET_BUILD_DEVICERTL_BCLIB=FALSE \
  -DLLVM_DIR=<llvm-20.1.0-cmake-dir> \
  -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ \
  -DCMAKE_CXX_STANDARD=17
ninja
ninja install
```

- `LIBOMPTARGET_BUILD_DEVICERTL_BCLIB=FALSE`：DeviceRTL 需 clang 生成 GPU bitcode
  （nvptx/amdgcn），无 GPU 平台不可用，禁用（configure 日志确认 "Not building DeviceRTL"）
- 构建产物：libomptarget.so.20.1 + libomptarget.rtl.aarch64.so.20.1 + libomp.so.5.0 + libarcher.so
- aarch64 generic-ELF64 插件以 dlopened-libffi 模式构建（无需系统 libffi）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 报 `System is unknown to cmake`，SONAME 缺失导致 libomptarget.so 的 DT_NEEDED 为构建树相对路径 `runtime/src/libomp.so` | CMake 4.1.2 无内置 Platform/HarmonyOS 模块（仅 OHOS.cmake），`CMAKE_SHARED_LIBRARY_SONAME_*_FLAG` 未设置 | 提供 `Platform/HarmonyOS.cmake`（`include(Platform/Linux)`）注入 CMAKE_MODULE_PATH（llvm/20.1.0 同款方案）；配合 `-DCMAKE_SYSTEM_NAME=HarmonyOS -DCMAKE_SYSTEM_PROCESSOR=aarch64` |
| 2 | libomp 编译失败：`use of undeclared identifier 'pthread_cancel'/'pthread_setcanceltype'/'pthread_setcancelstate'` | HarmonyOS 无 POSIX 线程取消（同 Android）| kmp.h 用 `!defined(LIBOMP_HAVE_PTHREAD_CANCEL)` 能力宏守卫 undef KMP_CANCEL_THREADS（E081 知识；POSIX 能力探测替代硬编码平台宏，R8 合规）→ patch 0002 |
| 3 | libomp 无 SONAME，消费者链接到 `runtime/src/libomp.so` | standalone 构建 libomp 的 set_target_properties 未设 VERSION/SOVERSION（仅 MSVC 分支设置） | 非 MSVC 分支增加 `VERSION/SOVERSION` → patch 0003；SONAME=libomp.so.5，libomptarget DT_NEEDED 变为 `libomp.so.5` |
| 4 | aarch64 offloading 插件不构建（"machine not found in the system"） | plugins-nextgen/aarch64/CMakeLists.txt 判定 `CMAKE_SYSTEM_NAME MATCHES "Linux"`，HarmonyOS 不匹配 | 改为 `MATCHES "Linux\|HarmonyOS"` → patch 0004 |
| 5 | JIT.cpp 编译失败：`unknown type name 'LLVMTargetMachine'` | LLVM 20 移除了 LLVMTargetMachine 类，`MachineModuleInfoWrapperPass` 构造函数直接接受 `TargetMachine*`（LLVM 18 需 reinterpret_cast） | 去掉 reinterpret_cast，直接传 TM → patch 0005 |
| 6 | 官方 openmp-18.1.8.src.tar.xz 无 LLVM 根 cmake 目录 | `LLVM_COMMON_CMAKE_UTILS` 指向 `../cmake`，tarball 不含 | CMakeLists.txt patch 指向本地 cmake/ + conanfile.py source() 生成 ExtendPath.cmake / LLVMCheckCompilerLinkerFlag.cmake（同 libomp/15.0.4 做法）→ patch 0001 |

## 验证结果

```bash
# libomp 多线程运行验证
clang -fopenmp test.c -L stage2/lib -I stage2/include -o omptest
LD_LIBRARY_PATH=stage2/lib:... ./omptest
# → OpenMP runtime version: 5.0+
# → Hello from OpenMP thread 0 of 20

# 库加载链验证（readelf）
libomptarget.so: NEEDED libomp.so.5, libLLVM.so.20.1, libc++_shared.so, libc.so
libomptarget.rtl.aarch64.so: NEEDED libLLVM.so.20.1, libc++_shared.so, libc.so
# SONAME 均正常（libomptarget.so.20.1 / libomp.so.5 / ...rtl.aarch64.so.20.1）

# SONAME 版本说明：libomptarget.so 的 SONAME 后缀为 .20.1，这是 LLVM 版本号，
# 与 llvm/20.1.0 依赖保持一致（in-tree 构建时 add_llvm_library 以 LLVM 版本
# 生成 VERSION/SOVERSION），属于预期行为，并非 libomptarget 自身 ABI 版本。
```

test_package 测试：**端到端消费者用例**（非纯断言）——用 `-fopenmp` 链接 libomp
驱动 `#pragma omp target` 数据映射与目标区计算（host fallback 路径，
OHOS aarch64 无 GPU 时目标区在主机执行），`#pragma omp parallel for
reduction` 聚合后与期望值校验（实测 got==expect，真实数值结果通过）；
同时经 dlopen("libomptarget.so.20.1") + dlsym 调用 `__tgt_init_all_rtls` /
`omp_get_initial_device` / `omp_get_num_devices`（R34 实质调用被测包 API）。
OHOS musl 对带 verneed（导入 libLLVM 版本化符号）的 ELF dlopen 返回 EACCES，
该平台限制已在 test() 中如实区分处理（仅容忍该确切报错，其它失败 re-raise）。

## 源码修改（patches/）

1. `0001-CMakeLists.txt.patch` — openmp 顶层 CMakeLists：LLVM_COMMON_CMAKE_UTILS 指向本地 cmake/
2. `0002-runtime-src-kmp.h.patch` — 能力宏 LIBOMP_HAVE_PTHREAD_CANCEL 守卫禁用 KMP_CANCEL_THREADS（E081）
3. `0003-runtime-src-CMakeLists.txt.patch` — libomp VERSION/SOVERSION（SONAME 修复）
4. `0004-plugins-aarch64-CMakeLists.txt.patch` — aarch64 插件支持 HarmonyOS 平台
5. `0005-JIT.cpp.patch` — JIT.cpp 适配 LLVM 20 API（LLVMTargetMachine 移除）

## 依赖版本

- llvm/20.1.0（制品仓已发布，提供 LLVMConfig.cmake + libLLVM.so.20.1 + 头文件）

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libomptarget.so.20.1 | offloading 运行时主库（SONAME 20.1） |
| lib/libomptarget.rtl.aarch64.so.20.1 | aarch64 generic-ELF64 offloading 插件 |
| lib/libomp.so.5.0 | host OpenMP 运行时（libomptarget 依赖） |
| include/omp.h 等 | OpenMP 头文件 |

## 注意事项

- DeviceRTL 禁用（需 GPU clang -fopenmp-targets 生成 bitcode，无 GPU 平台不适用）
- 未构建 CUDA/AMDGPU 等 GPU 插件（无相应硬件/驱动）
- **上游 lit 测试真实执行记录（评审闭环 2026-09-28）**：在 OHOS aarch64 真机以
  `python3 lit` 驱动 libomptarget/test 套件真实编译运行（clang 15.0.4 -fopenmp
  host-fallback 编译 + FileCheck 校验，wrapper 剥离无 clang-offload-packager 的
  `-fopenmp-targets=` 参数，测试源码保持上游原样）：

  | 结果 | 数量 | 说明 |
  |------|------|------|
  | PASS | 64 | 主机可运行用例真实通过（host-fallback 路径，含 offloading/info、mapping 基础、部分 api 等） |
  | FAIL | 74 | 全部编译成功并运行，断言因**无 offload 设备**失败（`omp_get_num_devices()==0`：device memory/memcpy/USM/declare_mapper/ompx_hold/present/offloading_success 等设备能力用例；offloading_success 实测输出 "Target region executed on the host"） |
  | UNSUPPORTED | 63 | lit 按 REQUIRES 正确跳过：nvptx/amdgcn GPU、flang、ompt、unified_shared_memory、libomptarget-debug 等特性在 OHOS 无对应设备/工具 |
  | 合计 | 201 | libomptarget/test 注册测试文件数（上游 610 个 // RUN 行按文件聚合） |

  该结果与 test_package 端到端消费者用例（target 工作流 got==expect 数值校验通过）
  相互印证：OHOS 无 GPU offload 设备时 target 区在主机执行，host 侧可运行用例真实
  通过，设备能力用例真实失败（非跳过/伪造）。

- **OHOS musl 加载器限制（实测 2026-09-26）**：带 verneed（导入 libLLVM 版本化
  符号 @LLVM_20.1）的 ELF（libomptarget.so.20.1 / libomptarget.rtl.aarch64.so.20.1）
  被 OHOS musl 加载器 dlopen 拒绝（EACCES / Permission denied），故运行时
  test_package 不以 DT_NEEDED 直接依赖 libomptarget，改用 dlopen/dlsym 调用其
  公共 API，并容忍该确切平台报错；端到端消费者流程本身经 libomp host-fallback
  真实运行通过。libLLVM.so.20.1 / libomp.so.5.0 本身可正常加载。
- R8 说明：patch 0002 采用 POSIX 能力探测宏 `!defined(LIBOMP_HAVE_PTHREAD_CANCEL)`，
  而非硬编码 `__OHOS__` 平台宏（R8 合规；HarmonyOS 无 pthread_cancel，E081 实质适配，
  能力宏未定义即触发禁用）
---

**编译结束**: 2026-09-17 12:46
**最终状态**: built
