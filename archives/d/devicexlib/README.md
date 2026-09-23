# deviceXlib

deviceXlib 是 MaX Centre（欧洲纳米电子中心卓越中心 "MaX" 合作项目）发布的 Fortran 设备抽象层：把 CPU/GPU 上的内存分配、映射、拷贝、初始化、pinned 内存与 BLAS/LAPACK 线性代数封装为统一的 Fortran 接口，供 Quantum ESPRESSO 等 MaX 组件在不同加速后端（CUDA Fortran / OpenACC / OpenMP GPU offload）间移植。

## 功能概述

- 内存管理：malloc/allocated/free、map/unmap、memcpy（d2d/d2h/h2d/h2h）、memset、pinned 内存
- 线性代数：gemm/gemv/axpy/dot 等 BLAS/LAPACK 封装（host/device 统一接口）
- 加速后端：CUDA Fortran（NVHPC）、OpenACC（NVHPC/GNU）、OpenMP GPU offload（IntelLLVM）三选一；BLAS offload 支持 CUBLAS/MKLGPU/ROCBLAS
- 双构建系统：autotools（config/configure → make.inc）与 CMake（≥3.21）并行维护

## OHOS 适配

- 语言构成 98.8% Fortran（C 仅 src/devxlib_missing.c 34 行），CMake `project(... LANGUAGES Fortran C)` 硬依赖 Fortran 编译器；OHOS 设备与 SDK 均无 gfortran/flang，使用本仓 `flang-ohos/20.1.0`（设备原生 LLVM Flang 工具链包）作 `tool_requires`
- flang-ohos 是精简运行集（无 clang builtins/crt）：编译需 `--sysroot=<SDK>/sysroot -resource-dir=<SDK>/llvm/lib/clang/15.0.4`，链接需补 SDK `llvm/lib` 与 `libFortranRuntime.a/libFortranDecimal.a`
- 上游 CMake 的三种 GPU 加速选项各带编译器门禁（只认 NVHPC/PGI/GNU/IntelLLVM），补丁新增 `DEVXLIB_ENABLE_ACC=OFF` / `DEVXLIB_ENABLE_GPU_BLAS=OFF`（CPU-only）并支持 LLVMFlang 编译器
- CPU-only 路径不使用 OpenMP 编译开关（OpenMP 目标只在 OPENACC/OPENMPGPU 分支链接），上游 `find_package(OpenMP REQUIRED)` 门禁由 recipe 的 Find 模块 shim 确定性满足
- `find_package(LAPACK REQUIRED)` 同样由 shim 映射到 conan lapack/3.12.1 包（自带 reference BLAS）
- 上游 `include/devxlib_version.h` 的版本字符串（0.8.5）与 git tag 0.9.1 脱节，归档以 tag 为准

## 依赖关系

- 编译依赖：flang-ohos/20.1.0（Fortran 编译器，tool_requires）、lapack/3.12.1（含 reference BLAS）
- 运行依赖：libFortranRuntime/libFortranDecimal（已随包分发）、LAPACK/BLAS（消费方经 conan 依赖闭包获得）

## 参考资料

- 主页/仓库：https://gitlab.com/max-centre/components/devicexlib
- MaX Centre：http://www.max-centre.eu/
- 下游使用：Quantum ESPRESSO（devXlib 为其设备抽象层）
