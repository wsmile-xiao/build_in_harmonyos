# OpenFAST 5.0.0 适配笔记

## 编译环境
- 构建系统: cmake（设备原生，os=OHOS arch=armv8，build=host）
- 编译器: clang/clang++ 15.0.4（SDK）+ tool_requires flang-ohos/20.1.0（LLVM Flang 20.1.0，Fortran）
- 依赖: openblas/0.3.34（BLAS+LAPACK）
- 测试: `BUILD_TESTING=ON` + `BUILD_UNIT_TESTING=ON`，上游 unit_tests 由 build() 内 `cmake.test()` 执行
- 状态: built

## 编译步骤
```bash
conan create archives/o/openfast/5.0.0 -pr:h ci/conan/profiles/ohos-aarch64 --build=missing
```

## 配方要点
1. `tool_requires flang-ohos/20.1.0` 提供 Fortran 编译器（`<pkg>/bin/flang`），
   `CMAKE_Fortran_COMPILER` 指向它；CMake 原生探测即可得到
   `CMAKE_Fortran_COMPILER_ID=LLVMFlang`（无人工干预，见补丁 0003）。
2. Fortran 编译与链接共用 `CMAKE_Fortran_FLAGS`（链接行含 `<FLAGS>`）：
   `-fPIC -fno-backslash -cpp`（`-fno-backslash -cpp` 由上游 `set_fast_flang()` 追加）
   `--target=aarch64-linux-ohos --sysroot=<SDK sysroot> -resource-dir=<SDK clang 15.0.4 resource>`。
   **`-resource-dir` 是链接成功的关键**：缺它时 Flang 去 `<flang pkg>/lib/clang/20/...` 找
   `libclang_rt.builtins.a` 与 `crtendS.o`，必然失败。
3. 链接标志补 `-L<sdk>/llvm/lib/aarch64-linux-ohos`（SDK 仅在该目录提供 `libunwind.a`，
   Flang 驱动会 `-l:libunwind.a`），且**三条规则都要给**：
   `CMAKE_EXE_LINKER_FLAGS` / `CMAKE_SHARED_LINKER_FLAGS` / `CMAKE_MODULE_LINKER_FLAGS`。
   共享库规则不含 `<CMAKE_Fortran_LINK_FLAGS>` 占位符，只设它会令 `*.so` 链接缺 `libunwind.a`。
4. **Fortran 链接驱动保持 flang，不用 clang 顶替**：SDK clang 顶替虽可让构建期全绿，
   但产物消费者在加载期会因 Fortran 运行时符号缺失而失败（#2944 netcdf-fortran 实测反模式）。
5. BLAS/LAPACK：`BLAS_LIBRARIES`/`LAPACK_LIBRARIES` 直接指向 `<openblas>/lib/libopenblas.so`
   （上游顶层 `find_package(LAPACK)` 找不到即 FATAL_ERROR）。
6. 最小模块集：FAST.Farm / C++ API / C++ Driver / Library Driver / Simulink / OpenMP 全部保持
   上游默认关闭；`DOUBLE_PRECISION=ON`（上游默认双精度）。
7. 上游单元测试：`BUILD_TESTING=ON` + `BUILD_UNIT_TESTING=ON`，build() 内先
   `cmake.build(target="unit_tests")`（unit_tests 是自定义目标、不属 ALL）再 `cmake.test()`；
   测试运行期需要 openblas 的 lib 目录（nwtclibs 链接 `libopenblas.so`），配方在 build() 期间
   注入 `LD_LIBRARY_PATH` 并在 finally 中复原。
8. 安装产物执行 `binary-sign-tool` 自签（被 exec 的 `bin/*` 与被 dlopen 的 `*.so`）；
   签名器与 `llvm-objcopy` 是 C++ 程序，必须用 `env -u LD_LIBRARY_PATH` 清掉构建期注入的
   `LD_LIBRARY_PATH`（否则同名 libc++ 遮蔽 → `symbol not found` → Error 127）。

## 源码补丁（7 个，per-file；`patches/` 与 conandata.yml 声明同步）

| 补丁 | 类型 | 内容 |
|---|---|---|
| 0001-ohos-unix-platform-guards.patch | portability | CMake 4.x 对 `CMAKE_SYSTEM_NAME=HarmonyOS` 不设 `UNIX` 变量 → nwtc-library 无法确定 `NWTC_SYS_FILE`、各模块 `IMPLICIT_DLLEXPORT` 分支不命中。7 个 CMakeLists 的 `if(APPLE OR UNIX)` → `if(NOT WIN32)` |
| 0002-fix-undefined-cotan-in-modvar.patch | bugfix | 上游缺陷：`nwtc-library/src/ModVar.f90` 的 `rvec_to_tan_inv` 调用 `cotan()`，而该函数在 v5.0.0 **全仓无任何定义**（模块内 `implicit none` 生效）→ 数学等价改写为 `1.0_R8Ki/tan(...)` |
| 0003-accept-llvmflang-compiler-id.patch | portability | LLVM Flang 20 新驱动被 CMake 识别为 `LLVMFlang`，上游白名单只认 `GNU/Intel/Flang` → `cmake/OpenfastFortranOptions.cmake` 白名单与分派、`nwtc-library/CMakeLists.txt` 的 `NWTC_SYS_FILE` 分支加入 `LLVMFlang` |
| 0004-guard-omp-lib-use.patch | portability | `aerodyn/src/FVW.f90` 与 `FVW_BiotSavart.f90` 未开 OpenMP 仍无条件 `use OMP_LIB`（二者无任何 `omp_*` 过程调用，仅 `!$OMP` 指示符），而 flang-ohos 不提供 OpenMP Fortran 支持（无 `omp_lib.mod`）→ 按上游代码内注释加 `#ifdef _OPENMP` 守卫 |
| 0005-fix-errmsg-transfer-extent.patch | bugfix | 上游缺陷：`FAST_Library.f90` 的 `FAST_CFD_Solution0` 中 `TRANSFER( ErrMsg, ErrMsg_c )` 源串 1024 字符（模块变量 `CHARACTER(IntfStrLen-1)`）对目标数组 1025（`IntfStrLen`）→ Flang 报 extent 不匹配；按同文件其余 31 处写法补 `//C_NULL_CHAR` |
| 0006-guard-regtests-without-submodule.patch | portability | `BUILD_TESTING=ON` 时顶层先 `add_subdirectory(reg_tests)`，而 reg_tests 需要 `reg_tests/r-test` 数据子模块（官方源码包不含，仅有空占位目录）→ 改为按内容判定（`reg_tests/r-test/glue-codes` 存在才注册），使 unit_tests 可在不引入 r-test 数据的前提下构建执行 |
| 0007-fix-transfer-size-in-c-binding.patch | portability | Flang `TRANSFER` 尺寸语义适配：`NWTC_C_Binding.f90` 的 `SetErrStat_F2C` 把短字符串 `TRANSFER` 到 8197 元素数组，Flang 按源串大小给结果（运行期 `Assign: mismatching element counts in array assignment (to 8197, from 14)`），F2018 规定结果大小 = MOLD 大小 → 显式加 `SIZE(ErrMsg_C)` |

补丁链黄金验证（2026-09-18 实测）：`HEAD + 0001 … 0007` 顺序应用后与构建工作树**逐字节一致**
（14 个文件全部 `diff` 为空）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `ld.lld: cannot open Scrt1.o / crtbeginS.o / libclang_rt.builtins.a`、`unable to find library -l:libunwind.a` | Flang 链接行缺 `-resource-dir` 与 `-L<sdk>/llvm/lib/aarch64-linux-ohos` | 见「配方要点」2、3；flang 全程驱动（**不**用 clang 顶替） |
| 2 | 共享库 `libifw_c_binding.so` 链接失败 | `-L` 只写进了 `CMAKE_Fortran_LINK_FLAGS`，而共享库链接规则不引用该变量 | 三条 linker flags 规则全部注入 |
| 3 | `error: No explicit type declared for 'cotan'`（ModVar.f90） | 上游 v5.0.0 未定义符号 | 补丁 0002 |
| 4 | `OpenFAST requires GFortran, Intel, or Flang Compiler. Compiler detected by CMake: flang` | 新 Flang 驱动的 ID 是 `LLVMFlang` | 补丁 0003 |
| 5 | `Cannot parse module file for module 'omp_lib'`（FVW_BiotSavart.f90） | 未开 OpenMP 却无条件 `use OMP_LIB`；flang-ohos 无 OpenMP Fortran 支持 | 补丁 0004 |
| 6 | `Dimension 1 of left-hand side has extent 1025, but right-hand side has extent 1024`（FAST_Library.f90） | `TRANSFER` 源/目标长度不一致（Flang 严格，gfortran 容忍） | 补丁 0005 |
| 7 | `NEED SUBMODULE`：`BUILD_TESTING=ON` 时 reg_tests 缺 r-test 数据 | 官方源码包不含 r-test 数据子模块 | 补丁 0006（按内容判定后跳过注册） |
| 8 | `nwtc_library_utest` 运行期 `Assign: mismatching element counts in array assignment (to 8197, from 14)` | Flang 的 `TRANSFER` 结果尺寸按源串而非 MOLD 计算 | 补丁 0007（显式 `SIZE=`） |

补充：Flang 对 `C_LOC/C_F_POINTER` 非互操作类型、`NUMERIC_STORAGE_SIZE`（默认整型/实型不一致时）
等给出大量 warning，均为上游代码风格问题，非致命，未做处理。

## 上游测试说明（计数为实测）
- `unit_tests/CMakeLists.txt`：**6** 项 CTest 注册（`aerodyn_utest`、`beamdyn_utest`、
  `inflowwind_utest`、`nwtc_library_utest`、`versioninfo_utest` 共 5 项无条件 +
  `amrex_reader_utest` 需 `AMREX_READER` 且 `BUILD_FASTFARM`，最小构建下不注册）。
  **本包在 build() 内真实执行这 5 项**，CTest 输出 `100% tests passed, 0 tests failed out of 5`
  （耗时约 65 秒，其中 `aerodyn_utest` 约 64 秒）。
- `reg_tests/CTestList.cmake`：注册项 **200** 项回归测试（实际统计：`of_*` 83、`hd_*` 24、
  `ad_*` 17、`md_*` 15、`sd_*` 14、`seast_*` 10、`bd_*` 8、`ff_*` 7、`ifw_*` 6，其余为单例项）。
  执行依赖 git submodule `reg_tests/r-test`（仿真输入与校验基线数据，官方 tarball 不含）与
  Python 驱动脚本，本适配**未执行**（未伪装执行，MANIFEST.yml 与 manifest.yaml 如实声明）。

## 验证结果
- `conan create archives/o/openfast/5.0.0 -pr:h ci/conan/profiles/ohos-aarch64 --build=missing`
  exit_code=0（官方源下载，日志见 learninglog `conan-create-10.log`）
- 上游单元测试：CTest `100% tests passed, 0 tests failed out of 5`
- test_package（消费者视角）：
  - `bin/openfast -v` 版本冒烟（banner 含 OpenFAST 版本、`Compiler: flang version 20.1.0`、
    `Precision: double`、`OpenMP: No`）
  - `smoke`：`FAST_AllocateTurbines` + `FAST_DeallocateTurbines` 库级链路，3 断言全过
  - `abi`：按绝对路径 `dlopen(RTLD_NOW)` 被测包 `libopenfastlib.so` 并 `dlsym` 3 个 C 接口符号，
    5 断言全过（可捕获未解析符号/架构不符/签名失效等交付面缺陷）

## 上游 SHA256 双源核对
- Homebrew formula：`urls.stable` 为 git 方式（tag `v5.0.0` + revision `2895884d2be`），`checksum=`
  → 无 tarball sha256 可比
- FreeBSD ports：无 openfast 条目 → 无 distinfo
- 本地计算（官方 codeload tarball，106,076,972 字节）：
  `f84793e7e6e8e5c6b995f8c8727c5104f3f8d3729ea2aae095b86d770e60063a`
  （2026-09-18 二次下载复算一致；并与 gitcode 镜像同 commit 逐文件 diff 交叉验证内容一致，
  唯一差异为 `vs-build/CreateGitVersion.bat` 行尾符）

## 注意事项
- `bin/` 下除 `openfast` 外还有 16 个模块级 driver 可执行文件（上游 install 规则一并安装），
  均为被 exec 的 ELF，packaging 阶段统一自签。
- `openfastlib.so` 为上游硬编码 SHARED 目标（`BUILD_SHARED_LIBS=OFF` 不影响它），
  另含静态 `openfast_prelib.a` / `openfast_postlib.a`；后者被下游静态链接时需要 Fortran 运行时，
  故打包时一并放入 `libFortranRuntime.a` / `libFortranDecimal.a`（与 blas/openblas 先例一致）。
- 已知限制：可选模块（FAST.Farm、C++ API/Driver、Library Driver、Simulink、OpenMP）未启用；
  OpenMP Fortran 在 flang-ohos/20.1.0 不可用（无 `omp_lib.mod`），故 `OPENMP` 保持 OFF。
