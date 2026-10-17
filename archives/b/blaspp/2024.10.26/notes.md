# blaspp 2024.10.26 适配笔记（HarmonyOS PC / os=OHOS arch=armv8）

## 软件定位

BLAS++（https://github.com/icl-utk-edu/blaspp，UTK ICL / SLATE 项目）是对
BLAS/LAPACK 的现代 C++ 封装：模板 API + 显式向量化友好布局 + batch API，
BSD-3-Clause。它是 lapackpp 2024.10.26 的前置硬依赖（lapackpp CMakeLists
对 `find_package(blaspp)` 缺失即 FATAL_ERROR，公开头 `lapack/util.hh` 直接
`using blas::Layout/Op/Uplo/Diag/Side`——补丁跳过检查也绕不开编译期头依赖，
见 `$HOME/tmp/lapackpp-2024.10.26/w0-stoploss-research.md` §2.2）。本包
合入后 lapackpp 止损可解除。

## 构建方案（CMake，设备原生）

- 上游 CMake ≥3.17、`project(blaspp VERSION 2024.10.26 LANGUAGES CXX)`、
  C++17（`target_compile_features PUBLIC cxx_std_17`，与 profile cppstd=17 对齐）。
- `BUILD_SHARED_LIBS=OFF`（静态库；R26）、`build_tests=ON`（构建上游 tester，
  在 build() 内跑上游测试）、`gpu_backend=none`（鸿蒙无 GPU 后端，可选依赖
  显式禁用）、`use_openmp=OFF`。
- 安装面：`libblaspp.a` + `include/blas.hh` + `include/blas/*.hh` + 构建树
  生成的 `include/blas/blas/defines.h`（defines.h.in 经 configure_file 落
  构建树）+ `lib/cmake/blaspp/`（blasppConfig/blasppConfigVersion/
  blasppTargets）。

## BLAS/LAPACK 后端探测（本包核心技术点）

上游 `cmake/BLASFinder.cmake` / `LAPACKFinder.cmake` 用 try_compile/try_run
探测 BLAS 候选（default/MKL/ESSL/OpenBLAS/Accelerate/generic `-lblas` 等）。
鸿蒙侧有两个不匹配：

1. 候选 `-lblas` 名称探测无法感知参考 BLAS 的 Fortran 运行时依赖
   （`libblas.a` 的 xerbla.o 引用 `_FortranAio*`，裸 `-lblas` 链接必失败，
   同 blas/3.12.1 包笔记）。
2. 设备/CI 上 `CMAKE_SYSTEM_NAME=HarmonyOS` → CMake 视为交叉编译，
   try_run 跳过运行、由 finder 按「能链接即视为可用」处理——这是上游显式
   支持的路径（finder 内有 `CMAKE_CROSSCOMPILING` 分支）。

本配方走 finder 内置的第一候选 **`BLAS_LIBRARIES` 直通**：缓存变量直接给定
库清单（全路径），finder 只对该清单做修饰/整型宽度探针（mangling ADD_ →
LP64 首位命中即停，确定性选择）。清单与静态链接拓扑序（GNU 单遍语义下也
安全，消费者在提供者之前）：

```
BLAS_LIBRARIES  = liblapack.a;libcblas.a;libblas.a;libFortranRuntime.a;libFortranDecimal.a;m
LAPACK_LIBRARIES = liblapack.a;libFortranRuntime.a;libFortranDecimal.a;m
```

- lapack.a（BLAS 符号消费者）在 libblas.a（提供者）之前；cblas 同理。
- 依赖包：`lapack/3.12.1`（ohpcd 已发布，内含参考 LAPACK+BLAS+flang 运行时）、
  `cblas/3.12.1`（ohpcd 已发布，tester 需要 cblas.h/cblas_* 符号）。
- CBLASConfig 探针（`config/cblas.cc` 含 `<cblas.h>`、链接 `-lcblas`）依赖
  编译器搜索路径：build() 设 `CPATH`（头）与 `LIBRARY_PATH`（-l 搜索）指向
  cblas 包 include/lib，仅作用于本构建会话。探测命中第一候选（空库清单，
  cblas 符号已在 BLAS_LIBRARIES 内），tester 链接行不再出现 `-lcblas`。
- Fortran 编译为零：本包纯 C++，flang 运行时只出现在链接期，无需
  flang-ohos tool_requires。

## testsweeper 的离线化（vendor/）

上游 tester 链接 testsweeper 库；`test/CMakeLists.txt` 用 FetchContent 在
**构建期**从 GitHub `git clone`（GIT_REPOSITORY + tag v2024.05.31）。构建期
网络依赖在 CI/设备上不可复现（网络受限、git 可用性不确定、tag 漂移面）。
处置：将同 tag 源码（sha256
64ac685f94132f71bde82d4ac38021dfe2c42dc3d2387829d1d26dc91e805f9d，BSD-3）
以**解包源码形态**随配方导出（`vendor/testsweeper-2024.05.31/`），经
FetchContent 官方变量 `FETCHCONTENT_SOURCE_DIR_TESTSWEEPER` 指向本地目录，
上游 CMakeLists **零改动**。

## 上游测试

- 入口：`test/run_tests.py`（上游唯一测试入口，无 ctest/make check）。
  计划项 = 例程 × 参数集，一项即一次 tester 进程调用；静态定义共计
  **N = 90**（HOST 56 + DEVICE 34；取数命令见 test_package/MANIFEST.yml）。
- 统计主口径 = 计划项；tester 逐参数用例（testsweeper PASS/FAIL 行）为
  辅助口径，两口径分列不混用。
- 实跑：`python3 run_tests.py --quick --host`（HOST 56 项全部执行；--quick =
  上游 run_tests.py 文档定义的全例程 sanity 跑法，逐计划项仍走完整参数扫描，
  仅尺寸/步长集缩小）。实测：56 项全 pass、tester 逐用例行 5510 pass /
  0 FAIL（用例行 = tester status 列 `pass` 行；Elapsed 与逐项明细以
  `reports/test-report.md` 为准，随采信轮更新）。DEVICE 34 项 NOT_RUN
  （gpu_backend=none，不写 PASS）。
- medium 全尺寸未跑（量化依据，2026-09-22 设备实测，原始日志留存任务目录）：
  上游默认 `--host`（medium 尺寸）单轮 **09:35:19 起跑，11:06:56 被中止时
  已运行 91.6 分钟仍未完成**——56 个 HOST 计划项仅完成 37 项，最后发起的
  batch-gemm 计划项未返回；gemm medium 单项样本运行 5.5 分钟亦未完成即被
  中止。全量预计数小时，超出 CI conan create 3600s 超时预算；--quick 是
  上游自己的全例程 sanity 入口，56 项计划项无一项省略。
- 结果与计数：`conanfile.py` `_run_upstream_tests()` 写
  `blaspp_upstream_test_summary.txt`；取数命令与四分项见 PR 正文统计表。

## 已知限制

- gpu_backend=none：device/batch-device 计划项（34 项）与 device API
  不适用（鸿蒙无 CUDA/HIP/SYCL）。host API 面完整可用。
- OpenMP 关闭：batch 例程走单线程路径（上游 `use_openmp=OFF` 支持）。
- 静态库交付；`blasppConfig.cmake`（上游 install 生成）内嵌依赖绝对路径，
  conan 消费方走 CMakeDeps（package_info 已声明 cmake_file_name/target 名
  与 cpp_info.requires），不依赖该内嵌路径。
