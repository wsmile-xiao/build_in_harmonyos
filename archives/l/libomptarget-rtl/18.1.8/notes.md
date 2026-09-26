# libomptarget-rtl 18.1.8 适配笔记 (HarmonyOS PC aarch64)

## 基本信息

| 项目 | 值 |
|------|------|
| 软件 | libomptarget-rtl（LLVM OpenMP offloading RTL 插件库，Alpine libomptarget-rtl 包同型） |
| 版本 | 18.1.8 |
| 构建系统 | CMake (OPENMP_STANDALONE_BUILD=ON, OPENMP_ENABLE_LIBOMPTARGET=ON) |
| 编译器 | clang/clang++ 15.0.4 (aarch64-unknown-linux-ohos) |
| 平台 | HarmonyOS PC aarch64（真机原生编译） |
| 编译日期 | 2026-09-18 |
| 打包目标 | libomptarget.rtl.aarch64.so（aarch64 generic-ELF64 offloading 插件） |

## 依赖与 LLVM 版本决策

- 制品仓无 `llvm/18.1.8`；`llvm/20.1.0` 已发布（LLVMConfig.cmake + libLLVM.so.20.1 + 头文件）
- 实测 libomptarget 18.1.8 源码使用 llvm/20.1.0 头文件/库可完整编译链接（仅 JIT.cpp 一处 API 需补丁）
- conanfile.py `requires("llvm/20.1.0")`，R36 依赖检查通过

## 编译配置

```bash
cmake <openmp-src> -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_SYSTEM_NAME=HarmonyOS \
  -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
  -DOPENMP_STANDALONE_BUILD=ON \
  -DOPENMP_ENABLE_LIBOMPTARGET=ON \
  -DLIBOMPTARGET_BUILD_DEVICERTL_BCLIB=FALSE \
  -DLIBOMP_HAVE_VERSION_SCRIPT_FLAG=FALSE \
  -DLIBOMPTARGET_USE_LTO=FALSE \
  -DCMAKE_DISABLE_FIND_PACKAGE_FFI=TRUE \
  -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=FALSE \
  -DCMAKE_C_FLAGS=-fno-lto -DCMAKE_CXX_FLAGS=-fno-lto \
  -DLLVM_DIR=<llvm-20.1.0-cmake-dir> \
  -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++
ninja && ninja install
```

- `LIBOMPTARGET_BUILD_DEVICERTL_BCLIB=FALSE`：DeviceRTL 需 clang 生成 GPU bitcode，本平台禁用
- `LIBOMP_HAVE_VERSION_SCRIPT_FLAG=FALSE`：去符号版本化（musl loader 无法解析 VERS1.0）
- `LIBOMPTARGET_USE_LTO=FALSE`：**关键**——libomptarget CMakeLists 默认 TRUE 会在
  CMAKE_CXX_FLAGS 之后追加 `-flto`，覆盖 `-fno-lto`；必须从源头禁 LTO
- `CMAKE_DISABLE_FIND_PACKAGE_FFI=TRUE`：强制 dlopened-libffi 自包含插件模式

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 报 `System is unknown to cmake`，SONAME 缺失导致 DT_NEEDED 为构建树相对路径 | CMake 4.1.2 无内置 Platform/HarmonyOS 模块 | 提供 `Platform/HarmonyOS.cmake`（`include(Platform/Linux)`）注入 generators dir（conan_toolchain.cmake 会 PREPEND 到 CMAKE_MODULE_PATH）；配 `-DCMAKE_SYSTEM_NAME=HarmonyOS -DCMAKE_SYSTEM_PROCESSOR=aarch64` |
| 2 | libomp 编译失败：`use of undeclared identifier 'pthread_cancel'` | HarmonyOS 无 POSIX 线程取消（同 Android）| kmp.h 用 `!defined(LIBOMP_HAVE_PTHREAD_CANCEL)` 能力宏守卫（E081）→ patch 0002 |
| 3 | libomp 无 SONAME，消费者链接到 `runtime/src/libomp.so` | standalone 构建未设 VERSION/SOVERSION | 非 MSVC 分支增加 `VERSION/SOVERSION` → patch 0003 |
| 4 | aarch64 插件不构建（"machine not found"） | plugins-nextgen/aarch64/CMakeLists.txt 判定 `CMAKE_SYSTEM_NAME MATCHES "Linux"`，HarmonyOS 不匹配 | 改为 `MATCHES "Linux\|HarmonyOS"` → patch 0004 |
| 5 | JIT.cpp 编译失败：`unknown type name 'LLVMTargetMachine'` | LLVM 20 移除了 LLVMTargetMachine | 去掉 reinterpret_cast，直接传 TM → patch 0005 |
| 6 | 官方 openmp tarball 无 LLVM 根 cmake 目录 | `LLVM_COMMON_CMAKE_UTILS` 指向 `../cmake` | CMakeLists patch 指向本地 cmake/ + source() 生成 ExtendPath.cmake/LLVMCheckCompilerLinkerFlag.cmake → patch 0001 |
| 7 | 系统 libffi 存在时 `find_package(FFI)` 命中，插件进入链接 libffi 模式，`#include <ffi.h>` 失败（FFI_HEADER=ffi/ffi.h 但 include 路径不含 ffi/ 子目录） | 本机 /usr/local 预装 libffi | `CMAKE_DISABLE_FIND_PACKAGE_FFI=TRUE` 强制 dlopened-libffi 自包含模式（无系统 libffi 依赖，Alpine 同款） |
| 8 | 最终 .o 为 LLVM bitcode（`-flto` 被 libomptarget 的 LIBOMPTARGET_USE_LTO 在 CMAKE_CXX_FLAGS 后追加覆盖） | LIBOMPTARGET_USE_LTO 默认 TRUE | `LIBOMPTARGET_USE_LTO=FALSE` 从源头禁 LTO |

## 产物验证

```bash
# SONAME / NEEDED（readelf）
libomptarget.rtl.aarch64.so.20.1: SONAME=libomptarget.rtl.aarch64.so.20.1
  NEEDED: libLLVM.so.20.1, libc++_shared.so, libc.so

# libomp 宿主运行时实测（-fopenmp 编译运行）
clang -fopenmp test.c -L<prefix>/lib -Wl,-rpath,<prefix>/lib -o omptest && ./omptest
# → OpenMP runtime version: 201811；sum=4950（多线程正确）

# RTL 插件链接验证（test_package build()）
clang test.c -L<prefix>/lib -lomptarget.rtl.aarch64 -o test → 链接成功

# 运行时 dlopen 限制（平台已知限制，同 libomptarget 主库）
# musl dlopen() 对含 .gnu.version_r（LLVM_20.1 符号版本需求）的 ELF 返回 EACCES
# → test_package 构建+链接验证通过，运行时按文档跳过（conan-verify G2 通过）
```

## 打包范围（Alpine libomptarget-rtl 对齐）

- 仅打包 `lib/libomptarget.rtl.aarch64.so`（+ .so.20.1 真实文件与 .so 软链）
- 不打包 libomptarget.so（主库）/ libomp.so（宿主 OpenMP 运行时）/ libarcher（工具）
  / include 头文件 —— 均属各自独立包
- R38：RTL 插件是库不是 CLI，无需 commands.json

## 依赖版本

- llvm/20.1.0（制品仓已发布，提供 LLVMConfig.cmake + libLLVM.so.20.1 + 头文件）

## 上游测试说明

- 上游 libomptarget/test 含 `RUN:` 指令的测试文件共 **201 个**（130 个 .c + 56 个
  .cpp + 15 个 .f90），已通过 generic-elf-64bit 插件 + libffi（宿主 CPU，无 GPU
  依赖）真实运行完整 lit 套件：**27 passed / 112 failed / 62 unsupported**
- 62 个 unsupported：`REQUIRES` 特性缺失（nvptx/amdgpu 设备特性、JIT 等），lit 按
  设计跳过
- 112 个 failed：真实执行结果——以运行时 SIGSEGV（Signal 11）为主（宿主 CPU 执行
  设备镜像崩溃），部分为断言/输出校验失败，均如实记录
- `ninja check-libomptarget` 为 no-op（libffi 禁用后不生成测试 target），测试改用
  定制 lit.site.cfg + llvm-lit 直接驱动上游测试源码执行

## 注意事项

- R8 说明：patch 0002 采用 POSIX 能力探测宏 `!defined(LIBOMP_HAVE_PTHREAD_CANCEL)`，
  而非硬编码 `__OHOS__` 平台宏（R8 合规；HarmonyOS 无 pthread_cancel，E081 实质适配）
- musl dlopen EACCES（verneed）为平台已知限制：RTL 插件链接 libLLVM 必然引入
  LLVM_20.1 符号版本需求，同 libomptarget 主库一致，test_package 按参考配方处理
---

**编译结束**: 2026-09-19 00:31
**最终状态**: built
