# tasmanian 8.2 适配笔记

## 概览

- 软件：tasmanian 8.2（Tasmanian Sparse Grids，美国橡树岭国家实验室的自适应稀疏网格工具箱）
- 类型：C++ 库（静态包）+ 命令行工具 `tasgrid`
- 依赖：无（`requires: []`）
- 构建系统：CMake（上游自带 CMakeLists，测试用 CTest）
- 目标平台：HarmonyOS PC（aarch64-linux-ohos，clang 15.0.4 / libc++ / CMake 4.1.2 / Conan 2.29.1）
- 适配路径：路径 A（基础适配，零补丁、零依赖）
- 状态: built

## 编译环境

```bash
conan create archives/t/tasmanian/8.2 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64
```

配方流程：

1. `source()` 解包上游 `v8.2` 官方 tarball（GitHub release，sha256 校验）。
2. `generate()`：`BUILD_SHARED_LIBS=OFF`，并把上游的全部可选加速项显式钉成上游默认值
   （`Tasmanian_ENABLE_BLAS/OPENMP/PYTHON/CUDA/HIP/DPCPP/MAGMA/MPI/FORTRAN/SWIG/DOXYGEN=OFF`），
   使包 id 稳定；OHOS 上按 E092 固定 `CMAKE_SYSTEM_NAME=Linux`。
3. `build()`：CMake 配置 + 构建（库、`tasgrid`、上游 examples 与测试二进制），随后在
   构建目录内执行 `ctest`——上游作为顶层工程会 `enable_testing()` 并注册 14 个回归套件，
   这样包的验证口径与上游 CI 一致。
4. `package()`：安装库、头文件、`bin/tasgrid`、上游 CMake config 与 LICENSE。
5. `test_package/`：消费者视角用例（21 个断言）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 打开 `Tasmanian_ENABLE_BLAS=ON` 后链接失败：`undefined symbol: _FortranACharacterCompareScalar1`（引用者 `dlange.o` / `zgelq.o` 等） | 制品仓 `openblas/0.3.34` / `blas/3.12.1` 由 `flang-ohos/20.1.0` 构建，但 flang 只是 `build_requirements`（tool_requires），Fortran 运行时 `libFortranRuntime.a` / `libFortranDecimal.a` 不向消费者传递 | 用 `lapack/3.12.1` 作闭包：它把两个运行时归档装进包内 `lib/` 并在 `cpp_info.libs` 声明（`lapack, blas, FortranRuntime, FortranDecimal`）。实测把 `BLAS_LIBRARIES` 指向 `openblas` + 两个运行时归档、`LAPACK_LIBRARIES` 指向 `liblapack.a` 后，15 个套件全部通过 |
| 2 | 即使链接成功，打开 BLAS 反而更慢：`SparseGridsRefinement` 单套件 13.07s → 629.75s，全套 59s → 657s | 制品仓 `lapack/3.12.1` 是未优化的 reference LAPACK；且上游用 `check_library_exists(zgelq_)` 探测 LQ 分解，静态闭包下探测未命中会打印 `using QR instead` 走 QR 路径 | 保持上游默认 `Tasmanian_ENABLE_BLAS=OFF`（上游自身默认即关闭）。已把结论写进版本级 manifest 的 `knowledge_gained`，供后续需要 BLAS 的数值库参考 |
| 3 | 打开 `Tasmanian_ENABLE_OPENMP=ON` 后 5 个套件无法运行：`Error loading shared library libomp.so` / `__kmpc_fork_call: symbol not found` | OHOS clang 15 支持 `-fopenmp`（独立小程序实测 `omp_get_max_threads()=8`，CMake `FindOpenMP` 报 found version 5.0），但构建产物在真机加载期解析不到 `libomp.so` | 保持上游默认 `Tasmanian_ENABLE_OPENMP=OFF`，14/14 套件全通过 |
| 4 | `conan create` 首次失败：`CMake Error at CMakeLists.txt:6: Parse error. Expected "(", got identifier with text "the"` | `test_package/CMakeLists.txt` 的注释续行被写坏（`# include ...` 的 `# ` 丢失），CMake 把该行当命令解析 | 改写注释后重跑，配置/编译/消费者测试全部通过（该问题与被测包无关） |

## 源码修改

无补丁（`patches_applied: []`）：上游源码、构建文件与测试用例零改动，全部差异通过配方注入。

## 依赖版本

- Conan 依赖：无（`requires: []`）
- 上游测试框架：CTest（CMake 自带，无需下载）
- 被评估但未启用的可选依赖：`openblas/0.3.34`、`lapack/3.12.1`（见上表第 1/2 条），
  OpenMP（libomp，见上表第 3 条）

## 验证结果

```text
代理创建（conan create archives/t/tasmanian/8.2，-pr:h/-pr:b=ci/conan/profiles/ohos-aarch64）
→ CREATE_RC=0

上游测试（build() 内 ctest --output-on-failure -j4）:
  1/14 SparseGridsAcceleration   Passed   6.32 sec
  2/14 SparseGridsDomain         Passed   0.54 sec
  3/14 SparseGridsRefinement     Passed  13.07 sec
  4/14 SparseGridsGlobal         Passed  20.83 sec
  5/14 SparseGridsLocal          Passed   4.20 sec
  6/14 SparseGridsWavelet        Passed  36.81 sec
  7/14 SparseGridsFourier        Passed   0.53 sec
  8/14 SparseGridsExceptions     Passed   0.05 sec
  9/14 SparseGridsAPI            Passed   0.03 sec
 10/14 SparseGridsC              Passed   0.03 sec
 11/14 DreamAnalytic             Passed   0.27 sec
 12/14 DreamModel                Passed   0.18 sec
 13/14 Optimization              Passed   0.04 sec
 14/14 AddonTests                Passed   4.47 sec
 → 100% tests passed, 0 tests failed out of 14（Total Test time (real) = 59.13 sec）

消费者测试（test_package）:
 → TASMANIAN_CONSUMER_CHECKS=21 FAILURES=0 → TASMANIAN_CONSUMER_OK
```

## 交付物

| 文件 | 说明 |
|------|------|
| `lib/libtasmaniansparsegrid.a` | 稀疏网格核心库（SparseGrids） |
| `lib/libtasmaniandream.a` | DREAM 优化/采样库 |
| `bin/tasgrid` | 命令行工具（软件级 `commands.json` 声明），`tasgrid --version` / `-v` 可用 |
| `include/**` | 67 个公共头（C++ 接口、C 接口 `TasmanianSparseGrid.h`、DREAM、Addons） |
| `lib/Tasmanian/*.cmake` | 上游 CMake package config（导出 `Tasmanian::Tasmanian`、`Tasmanian::tasgrid`） |
| `share/Tasmanian/**` | 上游 examples 源码与 CMakeLists、`GaussPattersonRule.table`、`TasmanianENVsetup.sh` |
| `licenses/LICENSE` | BSD-3-Clause with UT-Battelle disclaimer |

## 注意事项

- 本包为静态库：消费者链接受测包需带 C++ 运行时（配方 `package_info()` 已声明
  `system_libs = ["m", "pthread", "c++"]`，实测 `test_package` 静态链接通过）。
- 上游 examples 的源码随包交付在 `share/Tasmanian/examples/`，但 examples 二进制本身不是
  交付物；`Tasmanian.log` 是上游 install 时写出的构建日志（上游行为，未做删改）。
- 可选加速项（BLAS/OpenMP）在 OHOS 上均按上游默认关闭，原因与实测数据见上表；
  如需打开，请先解决 Fortran 运行时闭包与 `libomp.so` 加载问题。
---

**编译结束**: 2026-10-02 18:06
**最终状态**: built
