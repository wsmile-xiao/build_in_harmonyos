# lapackpp 2024.10.26 适配笔记（HarmonyOS PC / os=OHOS arch=armv8）

## 软件定位

LAPACK++（https://github.com/icl-utk-edu/lapackpp，UTK ICL / SLATE 项目）是
LAPACK 的现代 C++ 封装：模板 API + 显式向量化友好布局 + 强类型枚举，
BSD-3-Clause。与 `blaspp/2024.10.26` 同版本同上游发布，二者是 SLATE 的
前置中间层。

## 构建方案（CMake，设备原生）

- 上游 CMake ≥3.17、`project(lapackpp VERSION 2024.10.26 LANGUAGES CXX)`、
  C++17（`target_compile_features PUBLIC cxx_std_17`，与 profile cppstd=17 对齐）。
- `BUILD_SHARED_LIBS=OFF`（静态库；R26）、`gpu_backend=none`（鸿蒙无 GPU 后端，
  上游可选依赖显式禁用）、`build_tests=ON`（构建上游 tester 并在 build() 里
  真实执行上游测试，见「上游测试」节）。
- 安装面：`liblapackpp.a` + `include/lapack.hh` + `include/lapack/*.hh` +
  构建树生成的 `include/lapack/defines.h`（configure_file 落位，内含
  `LAPACK_HAVE_LAPACK` 与 `LAPACK_VERSION 31200`）+ `lib/cmake/lapackpp/`。

## LAPACK 后端探测（本包核心技术点）

上游 `cmake/LAPACKFinder.cmake` / `LAPACKConfig.cmake` 用 try_run 探针确定
LAPACK 后端与能力位。鸿蒙侧取「显式库清单直通」路径（用户给定缓存变量
`LAPACK_LIBRARIES` / `BLAS_LIBRARIES`，finder 逐项探针校验）：

```
BLAS_LIBRARIES  = liblapack.a;libcblas.a;libblas.a;libFortranRuntime.a;libFortranDecimal.a;m
LAPACK_LIBRARIES = liblapack.a;libFortranRuntime.a;libFortranDecimal.a;m;libopenblas.a（末位，仅测试拓扑）
```

- 顺序即静态链接拓扑序：liblapack.a（BLAS 符号消费者）在 libblas.a（提供者）
  之前，cblas 同理，Fortran 运行时收尾；libopenblas.a 末位（原因见
  「上游测试」节，交付库链接面不含它）。
- 依赖包：`blaspp/2024.10.26`（硬前置）、`lapack/3.12.1`（参考 LAPACK + 参考
  BLAS + flang Fortran 运行时）、`cblas/3.12.1`（openblas/0.3.34 经其
  `requires` 进图，版本被钉死，本配方传递访问、不直连）。
- **探针真跑**（非「能链接即通过」降级）：上游 LAPACKFinder/LAPACKConfig 用的是
  try_run（需执行），探针在鸿蒙/CI 环境均真实执行并给出真实结论：
  - `config/lapack_pstrf.cc` → 链接+运行成功 → `LAPACK_FOUND`、`-DLAPACK_HAVE_LAPACK`
  - `config/lapack_version.cc` → 运行输出 `LAPACK_VERSION=3.12.0` → `-DLAPACK_VERSION=31200`
    （版本是探针**实测**得来，不是配方里写死的；未定义该宏会让 20+ 个 src/*.cc 的
    `#if LAPACK_VERSION >= 30700` 分支静默走错分支，属必须保证的真实值）
  - `config/lapack_xblas.cc` → 链接失败（参考 LAPACK 无 XBLAS）→ 不加
    `-DLAPACK_HAVE_XBLAS`（符合参考实现的真实能力）
  - `config/lapacke_pstrf.cc` → **真实通过**，走上游内置的
    "Found LAPACKE library in BLAS library" 路径（详见「上游测试」节）
- Fortran 编译为零：本包纯 C++，Fortran 运行时只出现在链接期，无需 flang
  tool_requires。

## 与 BLAS++ 的对接（零补丁，配方侧完成）

上游对 blaspp 的依赖有两处「只做一半」的设计，原生构建（同前缀安装）下被
隐式满足，Conan 包布局下必须显式补齐。**本包零补丁**，全部在配方侧解决：

1. **两个私有配置变量**。上游 `find_package(blaspp)` 的唯一目的是取
   `blaspp_defines` / `blaspp_libraries`（上游 `blasppConfig.cmake.in` 注释
   "Export private variables used in LAPACK++"）。Conan 的 CMakeDeps 生成的
   `blaspp-config.cmake` **只导出导入目标、不导出这两个变量**，于是三个探针
   全部在 `config/config.h:19` 处 `#error "must define one of FORTRAN_ADD_, ..."`
   编译失败。
   配方侧：`tc.variables["blaspp_defines"]` 取自**已安装的 blaspp 包的
   `include/blas/defines.h`** 反解（该文件是 BLAS++ 构建期 configure_file
   生成的权威配置记录，本包实测得到 `-DBLAS_FORTRAN_ADD_;-DBLAS_HAVE_CBLAS`），
   **不硬编码命名修饰假设**——后端变化时不会静默链错符号；
   `blaspp_libraries` 与 `BLAS_LIBRARIES` 同源。
2. **BLAS++ 公共头的 include 路径**。上游从不把导入目标 `blaspp::blaspp` 链到
   lapackpp 目标上，而 `include/lapack/util.hh:15` 直接 `#include "blas.hh"`。
   配方侧用 CMake 官方注入点 `CMAKE_PROJECT_lapackpp_INCLUDE`（`project()` 之后
   立即 include）指向一个短桥接片段：`find_package(blaspp)` +
   `include_directories(${blaspp_INCLUDE_DIRS})`（目录作用域，早于 `add_library`）。
   片段同时桥接 tester 门禁变量 `blaspp_cblas_found` / `blaspp_cblas_include` /
   `blaspp_cblas_libraries`（同为上游私有导出；指向 openblas 包，见下节），
   并以 `link_directories` 解析 tester 链接行的裸 `-lblaspp`。上游 CMakeLists /
   源码**零改动**。
3. **`generators = "CMakeDeps"`**（配方类属性）：上游 `find_package(blaspp)` 是
   硬要求，缺 `blaspp-config.cmake` 即 FATAL_ERROR。
4. **未采用的替代方案（记录以免后人重走）**：不采用上游安装生成的
   `blasppConfig.cmake`——该文件内嵌**构建机绝对路径**
   （实测为 `/storage/Users/currentUser/.cache/conan2/...`），换机即失效；
   也不采用「openblas 整体顶替参考 LAPACK/BLAS 后端」——那会改变交付包的
   后端拓扑（cpp_info.requires 与消费者链接面）。本次实际采用的
   「openblas 仅作测试拓扑的 LAPACKE/CBLAS/BLAS 提供方」是**限定范围的第三
   路径**：libopenblas.a 只出现在测试构建的链接行（探针 + tester），交付库
   链接面与 cpp_info.requires 完全不变；tester 链接行上没有 libblas.a /
   libcblas.a（BLAS_*/cblas_* 符号全部由 libopenblas.a 单一提供，先于它扫描
   的 liblapack.a 只提供 LAPACK_* 符号），不存在符号重复问题。

## 上游测试（build_tests=ON，真实执行）

- 入口：`test/tester` + `test/run_tests.py`（上游无 ctest；CMake `check` 目标执行
  `run_tests.py --quick <12 例程子集>`）。统计主口径 = run_tests.py 计划项。
- **清点（实测，R51）**：test/test_*.cc 共 177 个 tester 翻译单元；run_tests.py
  计划项 **N = 181（HOST 177 + DEVICE 4）**。取数命令见
  `test_package/MANIFEST.yml`。
- **本次实际执行：HOST 177/177 全部 PASS，0 FAIL 0 SKIP；DEVICE 4 项 NOT_RUN**
  （`gpu_backend=none`，鸿蒙无 GPU 后端，不以任何形式上报为通过）。两轮完整
  `conan create` 结果逐项一致（可复现）。辅助口径（tester 逐用例行）：
  test-case PASS=4928 FAIL=0。  实测摘录（build/Release/test/lapackpp_host_quick.log 首项）：

  ```
  ./tester  --type s,d,c,z --align 32 --dim 100 gesv
  type       n    nrhs  align     error   time (s)  ...  status
     s     100      10     32  5.77e-10     0.0290  ...  pass
  ```

- **此前 0/181 的技术阻塞与本次的解法**（逐条，非「没环境」）：上游 tester 的
  构建在 `test/CMakeLists.txt` 内被硬门禁早退：

  ```cmake
  if (NOT blaspp_cblas_found)   # "CBLAS not found; tester cannot be built."
  if (NOT lapacke_found)        # "LAPACKE not found; tester cannot be built."
  ```

  tester 必须链接 **LAPACKE**（C 接口：`test/lapacke_wrappers.hh` include
  `<lapacke.h>`，`test/test.cc` 走 `LAPACKE_*` 校验路径），而提供 LAPACKE 的
  `lapacke/3.12.1` 配方虽已合入 main（`archives/l/lapacke/3.12.1`，
  manifest `status: built`），**至今未发布到 ohpcd 制品仓**。有效证据
  （R35：判定 binary 存在性须用 `conan download` / `conan install`，
  禁用 `conan list`）：

  ```
  conan install --requires=lapacke/3.12.1 -pr:h=ohos-aarch64-wsl -pr:b=ohos-aarch64-wsl
    -> ERROR: Package 'lapacke/3.12.1' not resolved: Unable to find
       'lapacke/3.12.1' in remotes. Required by 'cli'
  ```

  等待 lapacke 发布不再是必要条件：**openblas/0.3.34 自带全量 LAPACKE**
  （`include/lapacke.h`/`lapacke_config.h`/`lapacke_mangling.h`/`lapacke_utils.h`
  + `libopenblas.a` 内嵌 `LAPACKE_*` 符号，nm 实核；它本就是
  `cblas/3.12.1` 的既有传递依赖）。三个制约逐一解决（均零上游改动）：

  1. **LAPACKE 探测**：把 libopenblas.a 追加到 `LAPACK_LIBRARIES` 末位，上游
     `cmake/LAPACKConfig.cmake` 的 try_run 探针（编译并运行
     `config/lapacke_pstrf.cc`，qemu-aarch64 设备原生执行）走其内置的
     **"Found LAPACKE library in BLAS library"** 路径真实通过——非预置
     变量，上游探测逻辑原样生效（配置日志实录见上）。随之 `LAPACK_HAVE_LAPACKE`
     写入构建树 defines.h（交付包含它），上游源码零引用（grep 实核），无行为
     影响。
  2. **cblas 门禁**：`blaspp_cblas_found`/`blaspp_cblas_include`/
     `blaspp_cblas_libraries` 由桥接片段提供，指向 openblas 包（cblas.h 与
     CBLAS 符号的单一提供方）。
  3. **testsweeper 框架**：上游 CMake 用 FetchContent 从 GitHub 实时 git clone
     （构建期网络依赖，CI/设备不可复现），本配方将同 tag 源码
     （v2024.05.31，与上游 CMakeLists 钉死版本一致）以 `vendor/` 形态随配方
     导出，经 FetchContent 官方变量 `FETCHCONTENT_SOURCE_DIR_TESTSWEEPER`
     指向本地目录（与 blaspp 配方同款手法）。
  4. **头与裸 -l 的查找**：探针 try_run 不传递 include 目录（原生构建靠系统
     路径），以 `CPATH` 注入 openblas/blaspp 包 include（clang/gcc 同语义，
     只作用于本构建会话）；tester 链接行的 `-lblaspp`（上游
     `list(APPEND LAPACK_LIBRARIES "blaspp")`）由桥接片段 `link_directories`
     解析——本工具链 clang-15 **不**把 LIBRARY_PATH 环境变量翻译成 -L
     （实测：设置 LIBRARY_PATH 后仍 `unable to find library -lblaspp`），
     必须显式 -L。

  **tester 拓扑（与交付包后端解耦）**：liblapackpp.a（交付库）+ 参考 LAPACK
  （liblapack.a 先于 libopenblas.a 扫描：LAPACK_* 符号由参考实现提供，
  openblas 的 LAPACK 实现成员不被拉入）+ libopenblas.a（BLAS 内核 + CBLAS +
  LAPACKE 的单一提供方，tester 的 BLAS_*/cblas_*/LAPACKE_* 符号全部由它解析，
  与 blaspp_cblas_libraries 指向一致）+ Fortran 运行时收尾。此为「参考
  LAPACK 叠加 OpenBLAS BLAS/LAPACKE」的标准发行版组合形态，仅作用于测试构建。
  DEVICE 4 项 NOT_RUN 的申报口径与 blaspp（34 项 NOT_RUN，已过审）一致。
- **补全测试（实际执行）**：`test_package/test_lapackpp.cpp`，32 条**数值断言**
  （18 条既有单例程断言 + 14 条端到端管线断言），经 `self.run()` 真实执行
  aarch64 二进制，全部通过（实测 `TOTAL assertions=32 ALL PASSED`，两轮一致）：
  - 既有：版本宏/运行时函数、potrf 后 L·Lᵀ 回乘、gesv 求解 x=[0.8,1.4]、
    getrf+getrs 残差 <1e-10、trtri 后 M·M⁻¹==I、geqrf+orgqr 后 QᵀQ==I、
    syev 特征值 {1,3}、gesvd 奇异值 {3,2}；
  - **完整消费者用例**（第 9 节，n=60 确定性 SPD，可复现 LCG）：端到端数值
    管线 potrf→posv→porfs→pocon→syev/gesvd 交叉验证，验算一律走 blaspp 的
    BLAS 调用（gemm/gemv/nrm2），与真实消费者（SLATE）调用形态一致：
    max|L·Lᵀ−A|<1e-12、max|x−x_true|<1e-10、porfs berr<1e-14、
    0<rcond≤1、λmin>0、max|σᵢ−λᵢ|<1e-10·λmax（注意 dgesvd 降序/dsyev
    升序）、rcond 与 λmin/λmax 相差 <2 个数量级、全链路残差
    ‖A·x−b‖₂<1e-12。

## 踩坑记录（写测试/校验数值时实测得到，勿重复）

1. **LAPACK 只写 uplo 指定的三角形**：`potrf(Lower)` / `trtri(Lower, NonUnit)`
   之后严格上三角**保留原值不被清零**。做 L·Lᵀ、U·U⁻¹ 回乘前必须自行清零，
   否则数值断言假失败（本包首轮 3 条失败中的 2 条即此因）。
2. **`dsyev` 特征值按【升序】返回**（LAPACK 文档规定），不是常被误记的降序。
   已用同一输入直连参考 `dsyev_`（lapack/3.12.1）交叉验证：`W=[1,3]` 升序，
   lapackpp 的 `syev` 是薄封装，行为与后端一致，非适配缺陷。**对照：
   `dgesvd` 奇异值按【降序】返回**——用 SPD 的 σᵢ==λᵢ 做交叉验证时必须
   反序对齐（σᵢ↔λ_{n-1-i}），顺序写反断言必假失败。
3. **列主序三角阵的构造易错**：`{2,0,1,3}`（列主序）其实是**上**三角，
   `{2,1,0,3}` 才是下三角；配 `Uplo::Lower` 用前者会导致 LAPACK 只反解对角、
   另一半留原值，症状同上。
4. **`dpocon` 的 A 入参必须是 Cholesky 因子**（dpotrf/dposv 的输出），
   `anorm` 才是**原阵**的 1-范数（lansy 算原阵）——两个入参来自不同的矩阵，
   极易传错。实测传原阵会得到 rcond>1 的伪结果（首轮 e2e 断言
   `0 < rcond ≤ 1` 失败即此因），改传 posv 的分解输出后通过。
5. **本工具链 clang-15 不翻译 LIBRARY_PATH**（实测：`LIBRARY_PATH=<dir>` 下
   裸 `-lblaspp` 仍报 `ld.lld: unable to find library`）。裸 -l 名称必须用
   CMake `link_directories()` 显式给 -L；`CPATH`（头文件查找）则正常生效，
   两者别混为一谈。
6. **conan 2（2.29 实测）：direct requires 必须出现在
   `cpp_info.(components.)requires`**，否则 `package_info()` 报
   "The direct dependency 'X' is not used by any..."；`visible=False` 也躲不过
   （该依赖若同时经其他包的常规边进图，合并后节点仍是 visible）。测试专用
   依赖的正确姿势：**走传递路径**（`self.dependencies` 对传递依赖同样可索引，
   openblas 经 cblas 进图即此用法），不直连 require。
7. **tester 二进制名**：上游 `lapackpp_` 前缀仅在子项目场景（SLATE 内嵌）非空，
   顶层项目构建时 tester 就叫 `tester`，落在 `build/test/tester`——别按
   `lapackpp_tester` 找。

## 本地验证（W3，同 profile 同工具链）

- `conan create archives/l/lapackpp/2024.10.26
  -pr:h=ohos-aarch64-wsl -pr:b=ohos-aarch64-wsl`
  → **rc=0**（两轮完整运行，结果逐项一致）。全周期 = 库构建 + 177 个 tester
  翻译单元编译 + testsweeper + 177 计划项执行 + test_package，本地（WSL，
  aarch64 二进制经 qemu-aarch64 执行）全程约 25 分钟，其中 177 计划项实测
  10m46s——CI conan create 默认超时 3600s（`ci/conan/build_and_test.sh`
  DEFAULT_BUILD_TIMEOUT），余量充足。0 error，上游 HOST 177/177 PASS，
  test_package 32/32 断言通过。
- 本地 WSL 侧 aarch64 OHOS 二进制可真实执行（WSL 已注册 qemu-aarch64 binfmt），
  故上游 try_run 探针、177 个计划项与 test_package 均真跑，非「能链接即通过」。

## 已知限制

- gpu_backend=none：device 例程（上游 4 个 `*_device` 计划项）与 device API
  不适用（鸿蒙无 CUDA/HIP/SYCL），如实申报 NOT_RUN。host API 面完整可用，
  host 计划项 177/177 全过。
- 静态库交付；上游安装生成的 `lapackppConfig.cmake` 内嵌依赖绝对路径，Conan
  消费方走 CMakeDeps（`package_info` 已声明 cmake_file_name/target 名与
  `cpp_info.requires`），不依赖该内嵌路径。
- `lapacke/3.12.1` 发布到 ohpcd 后，如需把 tester 的 LAPACKE 提供方从
  openblas（内嵌）切换为独立 liblapacke，只需替换 LAPACK_LIBRARIES 末位与
  桥接变量指向，机制不变。

---

**编译结束**: 2026-09-29 19:05
**最终状态**: built（上游 HOST 177/177 PASS + 消费者 32/32 PASS）
