# devicexlib 0.9.1 适配笔记（HarmonyOS PC / os=OHOS arch=armv8）

- 日期：2026-09-11；Builder：oh-device-porting-v2 run `devicexlib-0.9.1`
- 上游：https://gitlab.com/max-centre/components/devicexlib tag `0.9.1`
  （2026-03-20，commit 287f964062551bb7db68a2524f21768b088b3006）
- 归档：`https://gitlab.com/max-centre/components/devicexlib/-/archive/0.9.1/devicexlib-0.9.1.tar.gz`
  SHA256 `900fe8b0849d451e7c541d00a1b92c723e0969bae47ebcabd295e14ebcc17d1e`（5498866 字节，设备侧已核验）
- license：MIT（LICENSE.txt）；`config/` 下构建脚本继承 Quantum ESPRESSO 的 GPLv2 头（构建脚本层面，随上游）

## 1. 语言构成与核心矛盾

- 98.8% Fortran（~97,676 行），C 仅 `src/devxlib_missing.c` 34 行，无 C++。
- CMake `project(devXlib ... LANGUAGES Fortran C)`：Fortran 是项目级硬语言。
- OHOS 设备 `which gfortran flang fc f90 f77` 全缺失；系统 gcc 实为 clang 15.0.4
  （aarch64-unknown-linux-ohos）；OHOS SDK LLVM 亦无 flang。
- 默认工具链下 CMake configure 的真实失败（Phase-A 探针，
  `phase-a-configure.log`）：

  ```
  CMake Error at CMakeLists.txt:3 (project):
    No CMAKE_Fortran_COMPILER could be found.
  ```

## 2. Fortran 编译器：flang-ohos/20.1.0（仓内既有 tool 包）

- 仓内 `archives/f/flang-ohos/`（manifest: built 2026-07-24）为设备原生编译的
  LLVM Flang 最小运行集（bin/flang + libLLVM/libMLIR/libclang-cpp.so.20.1 +
  libFortranRuntime/Decimal.a），本机 conan 缓存与 ohpcd 制品仓均有。
- 仓内先例：openblas 0.3.28/0.3.33/0.3.34、lapack 3.12.1 均以
  `tool_requires("flang-ohos/20.1.0")` 编译 Fortran。本 recipe 沿用同款模式。
- flang-ohos 是精简运行集（无 clang builtins/crt），链接需显式补：
  - 编译：`--sysroot=<SDK>/native/sysroot -resource-dir=<SDK>/native/llvm/lib/clang/15.0.4`
  - 链接：`-L<SDK>/native/llvm/lib/aarch64-linux-ohos -L<SDK>/native/llvm/lib
    -L<flang>/lib -lFortranRuntime -lFortranDecimal`
  - 运行 flang/lld：`LD_LIBRARY_PATH=<SDK>/native/llvm/lib:<flang>/lib`
    （前者给 lld 补 libxml2.so.16，后者给 flang 补 libLLVM/libMLIR/libclang-cpp）
- 手工冒烟（`hello.f90` 编译+链接+运行）在设备上全部通过。

## 3. CPU-only 路径与补丁

上游 CMake 的 GPU 三选项各有编译器门禁（CUDAF→NVHPC/PGI、OPENACC→NVHPC/PGI/GNU、
OPENMPGPU→IntelLLVM），GPU BLAS（CUBLAS/MKLGPU/ROCBLAS）亦然，且无 CPU 空档；
OHOS PC 无任何 GPU 路径可行（CUDA/MKL/rocblas 均不可用）。内置 BLAS
（extlibs/blas，reference BLAS 源码）同样是 Fortran，绕不开 Fortran 编译器，
因此真正路径 = flang + CPU-only：

- `patches/0001-cmake-cpu-off-option.patch`
  - `DEVXLIB_ENABLE_ACC`/`DEVXLIB_ENABLE_GPU_BLAS` 的 STRINGS 增加 `OFF`
    （CPU-only）；各编译器门禁分支在 OFF 时不触发。
  - 新增 `cmake/LLVMFlangCompiler.cmake`：定义 `compilerCustomConfig`
    INTERFACE 目标（上游只为 NVHPC/GNU/IntelLLVM 提供该目标）。
- `patches/0002-flang-async-kind-cpu.patch`
  - 症状：-j20 并行构建下，use 关联 kind 参数（dxl_async_kind，`= kind(0)`，
    由 devxlib_async 模块导出）在消费侧 kind 选择器处报
    "Must be a constant value"（42 处，集中于 devxlib_memcpy.f90:3458-3891）。
    实证机理：并行/HMDFS 下跨文件 .mod 非确定性损坏 → 消费侧常量求值失败的
    伪语义错误（最小判别探针与 pristine 全文件串行编译均通过；"接口体语义
    拒绝"初判已被探针证伪，详见 knowledge/drafts/
    DRAFT-flang-hmdfs-parallel-mod-corruption 与 reports/builder/draft-probes.log、
    repro-real.log）。引入 `DXL_ASYNC_DECL` 宏：GPU 构建展开为原文本，
    CPU-only 构建展开为等价的默认 `integer`（同时消除消费侧对导入参数
    常量保真的依赖）。涉及 devxlib_memcpy*.f90（5 个）、
    devxlib_auxfunc*.f90（2 个）、test_linalg/test_memcpy_async；同时把
    `use devxlib_async, only : dxl_async_kind`（及 auxfunc 的
    `private :: dxl_async_kind`）用 GPU 守卫包住，避免 CPU 下的
    "No explicit type declared" 语义错误。
  - `mod_rocblas.f90`：`module rocblas_enums` 整体在 `#if defined
    __DXL_ROCBLAS` 内，CPU 预处理下模块缺席，flang 不产 `.mod`，CMake 4 的
    Fortran 模块追踪（mod copy step）报 "Error copying Fortran module"。
    非 ROCBLAS 分支补一个占位空模块。
  - `src/CMakeLists.txt`：上游 0.9.1 的 CMake 源清单漏了 `devxlib_async.f90`
    （autotools 有）与 `prof_tools.f90`（test_linalg 依赖 `module myprof`），
    补入。
- `patches/0003-cmake-memset-test-target.patch`
  - 上游 CMake 源清单同样遗漏 `test_memset` target（autotools/TEST_LIST 有，
    28 项断言），且 `devxlib_memset_host.f90` 被 gated 在 CUDAF 分支——
    CPU-only 下 test_memset 链接缺 `devxlib_memset_h_*` 实现即由此而来
    （该文件为纯 CPU host memset 实现，autotools 无条件编译）。
    补丁补入 target 并将 memset_host 无条件编译，8/8 上游套件齐备。
- HMDFS 不支持 GNU make 的 FIFO jobserver（`make: jobserver mkfifo:
  Operation not permitted`，同 openblas notes 记载），并行下除模块编译乱序
  抢跑（.mod 未生成即被消费）外，还出现跨文件 .mod 读取非确定性损坏
  （伪语义错误 "Must be a constant value"，见上与判别探针）→ build 必须
  串行（`CMAKE_BUILD_PARALLEL_LEVEL=1`），这是正确性要求而非性能选择。
- `find_package(LAPACK REQUIRED)` / `find_package(OpenMP REQUIRED)`：
  FindLAPACK/FindOpenMP 的链接探测在 flang 精简运行集 + SDK 组合下不可靠，
  recipe 用确定性 Find 模块 shim：LAPACK 映射到 conan `lapack/3.12.1`
  （自带 reference BLAS），OpenMP 提供空 INTERFACE 目标（CPU-only 路径不
  链接 OpenMP target，仅上游 REQUIRED 门禁需要它成立）。

## 4. 依赖

- `requires: lapack/3.12.1`（仓内 recipe，设备原生 flang 构建，含 reference BLAS；
  需先构建入缓存，ohpcd 亦有 recipe）。devxlib_linalg 的 gemm/gemv/axpy/dot
  在链接期消费 BLAS/LAPACK 符号。
- `tool_requires: flang-ohos/20.1.0`。
- MPI 不需要；CUDA/MKL/rocblas 不可用且已通过 CPU-only 规避。

## 5. 构建与测试结果（设备原生）

- `conan create`（profile `ci/conan/profiles/ohos-aarch64`）：全绿。
- 上游测试（CMake 同树 **8** 个 test_*.x，与 autotools `make test` /
  `tests/run.sh` TEST_LIST 完全一致；test_memset target 由补丁 0003 补入），
  每套件输出重定向独立文件后回显，逐套件计数可复算（CI 日志
  reports/builder/ci-run-r2.log）：

  | 套件 | 运行时 npass（实然） | nfail | 源码静态断言结构数 |
  |---|---|---|---|
  | test_linalg | 16 | 0 | 16（npass=npass+1 结构数，一致） |
  | test_malloc | 28 | 0 | 28（一致） |
  | test_mapping | 28 | 0 | 28（一致） |
  | test_buffer | 10 | 0 | 静态不适用（devxlib_tester_fbuff 运行时计数，断言在循环内） |
  | test_memcpy | 28 | 0 | 28（一致） |
  | test_memcpy_async | 28 | 0 | 28（一致） |
  | test_memset | 28 | 0 | 28（一致） |
  | test_pinned | 10 | 0 | 静态不适用（同 buffer，tester 运行时计数） |
  | **合计** | **176** | **0** | — |

  口径说明（唯一可信口径 = 实然运行时输出）：6 个 npass 型套件的源码静态
  断言结构数与运行时 npass 完全一致（16/28/28/28/28/28）；buffer 与 pinned
  走 `devxlib_tester_fbuff` tester 类计数（n_tests−n_errors，断言位于循环
  内），静态计数不适用，以实然输出为准。此前文档中 "7 套件 166 项/pinned 28"
  为套件输出配对错误（pinned 实然 10），已全部订正。
- test_package：C 消费者链接 `libdevXlib.a`（含 libFortranRuntime/Decimal 与
  lapack 闭包）并运行通过（"devicexlib consumer link+run OK"）。

## 6. 其他事实与坑

- 上游版本字符串脱节：`include/devxlib_version.h` 写 0.8.5，tag 为 0.9.1；
  conandata 以 tag 0.9.1 为准。
- flang 20.1 对该 kind 选择器构造本身兼容：最小判别探针（module 参数 +
  use 关联 + interface body + submodule 实现 + IMPORT 变体）与 pristine
  全文件（5543 行、168 处构造）串行编译均通过；成批
  "Must be a constant value" 是并行/HMDFS 下跨文件 .mod 非确定性损坏的
  伪语义错误。机理与判别探针留档：tmp/oh-device-porting-v2/
  devicexlib-0.9.1-evidence/（探针脚本与输出）及
  reports/builder/draft-probes.log、repro-real.log、parallel-repro.log；
  详见 knowledge/drafts/DRAFT-flang-hmdfs-parallel-mod-corruption。
- 两次 -j20 强制重建复现尝试（force rebuild，每轮约 2 分钟）均未复现，
  与该故障的非确定性一致；维持"最可能机制"措辞并以串行构建为正确性
  约束（parallel-repro.log 归档于 reports/builder/）。
- CMake "System is unknown to cmake, create: Platform/HarmonyOS" 警告无害
  （conan toolchain 已设 CMAKE_SYSTEM_NAME=HarmonyOS，lapack 同款）。
- HMDFS 大文件复制/解包存在静默丢文件与可见性延迟（本轮 patch 生成阶段多次
  踩坑，最终改为在本机生成补丁后 scp；与仓内 gcc manifest 的 HMDFS 重试记录
  一致）。
- 设备默认 `ssh` 登录目录 getcwd 报错（Operation not permitted）为 shell 初始
  cwd 问题，不影响脚本内绝对路径 cd。

## 7. 复现

```bash
# 依赖先行入缓存（lapack，如缓存已清）
conan create archives/l/lapack/3.12.1 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 本包
conan create archives/d/devicexlib/0.9.1 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build='devicexlib/*'
# 权威 CI
CI_PACKAGES=archives/d/devicexlib/0.9.1 zsh ci/conan/build_and_test.sh
```
