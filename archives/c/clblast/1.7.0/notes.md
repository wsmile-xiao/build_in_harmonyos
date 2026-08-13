# clblast 1.7.0 适配笔记（HarmonyOS PC / aarch64）

## 定位
- 上游: https://github.com/CNugteren/CLBlast (Apache-2.0)
- 构建系统: CMake，产物 libclblast（OpenCL BLAS 库）
- 依赖: OpenCL（头文件 + libOpenCL.so）+ 测试期 CBLAS 参考

## 关键适配决策

### 1. OpenCL 依赖链
clblast 的 CMakeLists 在 `OPENCL=ON`（默认）时 `find_package(OpenCL REQUIRED)`，
且用的是**自带**的 `cmake/Modules/FindOpenCL.cmake`（非 CMake 内置），查找
`OpenCL/cl.h` 或 `CL/cl.h` + `libOpenCL.so`。
- 头文件来源: `opencl-headers/2026.05.29`（header-only，装到 include/CL/）
- 库来源: `opencl-icd-loader/v2024.05.08`（产出 libOpenCL.so）
- 由于是自研 find 模块而非 CMakeDeps config，配方在 generate() 里直接把
  `OPENCL_INCLUDE_DIRS` / `OPENCL_LIBRARIES` 变量喂给 CMakeToolchain。

### 2. 上游测试必须配 CBLAS 参考（否则被静默禁用）
CMakeLists 逻辑: `if(CLIENTS OR TESTS)` 时 `find_package(CBLAS/MKL/clBLAS)`，
若三者都找不到 → `message("disabling the compilation of the tests"); set(TESTS OFF)`。
也就是说**没有参考 BLAS，TESTS 会被静默关掉**，ctest 0 用例。
对策: 依赖 `openblas/0.3.33`，并把 `CBLAS_ROOT` 指向其 package_folder，
让自带 FindCBLAS.cmake 找到 cblas.h + libopenblas。测试程序默认以 CBLAS 为参考
（`CLBLAST_REF_CBLAS` 定义时 default_cblas=1）。

### 3. 上游测试构成（ctest，TESTS=ON）
- 51 个例程正确性测试 `clblast_test_<ROUTINE>`（level1 10 + level2 24 + level3 9 + levelx 8），
  每个覆盖精度 16/32/64/3232/6464，与 CBLAS 参考对比
- 3 个杂项测试（override_parameters / retrieve_parameters / preprocessor）
- ctest 注册共 54 个用例（assertion_count=54，见 test_package/MANIFEST.yml）
- 每个测试可执行文件**需要真实 OpenCL 设备**；设备不支持的精度会被跳过
  （打印 "All tests skipped: Unsupported precision"，不算失败）

### 4. 编译选项
- `TESTS=ON`（上游测试），`SAMPLES/TUNERS/CLIENTS/NETLIB/CUBLAS=OFF`（只出库）
- `CMAKE_POLICY_VERSION_MINIMUM=3.5`: 兼容较新 CMake（与 opencl-icd-loader 同款处理）
- 默认静态库（shared=False，与仓库惯例一致）

## 风险与待真机确认
- 真机是否有 OpenCL 平台/设备未知：若设备缺失，上游测试与 test_package 均会在
  设备初始化处失败（clGetPlatformIDs 返回 0），需如实记录而非伪造通过。
- openblas/opencl 系包是否已发布到 ohpcd 制品仓：conan create 时若缺包会直接报错，
  届时再决定 vendor 或等待发布。

## 验证命令（真机）
```
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

## 修复记录
- 2026-08-11（真机预检 compile 失败，`TypeError: CMake.test() got an unexpected keyword argument 'args'`）：
  Conan 2.x 的 `CMake.test()` 没有 `args` 参数（qhull 曾踩同坑）。改为
  `_run_upstream_ctest()`：subprocess 直接调 ctest（castxml 同款），
  `--test-dir` 指向 build 目录 + `--output-on-failure --no-tests=error`；
  运行前把 opencl-icd-loader / openblas 的 lib 目录追加到 LD_LIBRARY_PATH
  （测试可执行文件运行时需要 libOpenCL.so 与 libopenblas.so），
  解析 ctest 汇总行后打印 `HMBS_UPSTREAM_TEST_RESULT` 标记，非零退出直接
  让 conan create 失败（诚实，不伪造通过）。
- 真机 readonly_tmp 平台诊断（/tmp 只读、HNP bash 在 HMFS/HMDFS 上 getcwd
  失败）：test_package/conanfile.py 用 HMBS 注入的 `$SHELL=/bin/sh` 替代
  硬编码 bash，以 `$TMPDIR` 为 cwd、绝对路径调 test_clblast（addchain 同款），
  真实运行成功后打印 `HMBS_TEST_PACKAGE_RESULT` 标记。

## 本轮诊断 (2026-08-11, 真机预检 upstream_test 失败, clGetPlatformIDs: -1001)

**失败证据**: 53/53 个上游 ctest 用例全部 "Subprocess aborted"，统一报错
`OpenCL error: clGetPlatformIDs: -1001`（CL_PLATFORM_NOT_FOUND_KHR）。
OHOS PC 预检真机**未安装任何 OpenCL 平台/ICD 驱动**——opencl-icd-loader
自带的 test_package 也把 -1001 视为"无 OpenCL 硬件的构建机预期结果"。
上游 CLBlast 每个测试程序启动即 clGetPlatformIDs + 创建 OpenCL context，
无 OpenCL 设备则任何断言都无法执行。

**低成本补齐尝试（守则：先尝试低成本补齐，补不齐再放弃）**：
1. **tinyocl**（CLBlast 作者的最小 CPU OpenCL 实现，专为无 GPU 机器跑
   CLBlast 测试设计）：GitHub `CNugteren/tinyocl` 404，**仓库不存在**。
2. **PoCL / Oclgrind**（CPU OpenCL 实现）：均需 LLVM 工具链；仓库 llvm
   配方（17.0.0/20.1.0/22.1.0）状态 built 未发布到 ohpcd remote，且属
   独立库（单 PR 单库约束），超出低成本补齐范畴。
3. **真机 vendor ICD**：预检机无任何 OpenCL ICD 驱动（-1001 证据）。
→ **补不齐，按守则放弃**：上游 53 个用例已接入并在真机完整执行
（discovered=executed=53，无 no_tests/无自建替代/未删断言），通过率
如实写实际值 0/53，不伪造 100%，不删掉该栏。

**本轮工作树改动（未 commit，hmbs 预检通过后统一提交推送）**：
1. `conanfile.py`：`_run_upstream_ctest()` 标记新增审计字段
   `source_tree_total` / `opencl_dependent_unexecutable` / `reason`
   （astra 同款 device-discoverable 审计模型），数字仍来自 ctest 真实
   输出，非零退出仍让 conan create 失败（诚实）；用例数说明 54→53
   （level2 实测 23 个，10+23+9+8+3=53，与真机 ctest 发现数一致）。
2. `test_package/MANIFEST.yml`：`upstream_tests_exist: true` +
   `upstream_test_audit` 完整记录设备依赖审计、-1001 证据、低成本补齐
   尝试结论；assertion_count 54→53；level2 说明 24→23。
3. `notes.md`：本段诊断记录。

**PR 正文相关**: 上游测试用例通过率按真机实际值 0/53 填写；补充说明写
"上游 53 个用例未通过 + 缺 OpenCL 设备/驱动（真机无 OpenCL 平台）"。

## 本轮修复 (2026-08-11, 同一失败指纹第 2 次, 换策略: 低成本补齐探测)

**前次策略失效**: 上一轮「标记审计字段 + MANIFEST 审计 + 如实报 failed=53」
被 hmbs 拒绝——守则「存在失败或跳过，hmbs 都不会放行」，文档审计不改变
标记语义。本轮必须采用不同策略，不得原样重复。

**本轮根本不同策略 — 先探测并激活真机上可能存在的 OpenCL 实现**:

-1001（CL_PLATFORM_NOT_FOUND_KHR）是 Khronos ICD loader 在**默认搜索路径**
（/etc/OpenCL/vendors、/etc/OpenCL/vendors.d）找不到 vendor ICD 时的返回值。
OHOS PC 真机的厂商 OpenCL 驱动 ICD 常注册在 /vendor|/system|/odm/etc/
OpenCL/vendors，loader 默认不搜这些目录；且系统可能自带完整 libOpenCL.so
（非 loader）。此前直接断言「真机无 OpenCL 驱动」缺乏探测证据。

**改动（低成本补齐尝试，非伪造）**:
1. `conanfile.py` 新增 `_probe_opencl_runtime()`：ctest 运行前探测
   - vendor ICD 文件（/etc/OpenCL/vendors、/etc/OpenCL/vendors.d、
     /vendor/etc/OpenCL/vendors、/system/etc/OpenCL/vendors、
     /odm/etc/OpenCL/vendors 下的 *.icd）→ 设置 OCL_ICD_VENDORS；
   - 系统完整 libOpenCL.so（/system|/vendor|/odm|/lib|/usr/lib[64]）→
     前置到 LD_LIBRARY_PATH 优先加载；
   - 环境已有 OCL_ICD_VENDORS 则沿用。
   探测结果打印到日志（真机证据），并写入 HMBS_UPSTREAM_TEST_RESULT 的
   reason 审计字段。找不到实现时测试仍如实失败，绝不伪造通过。
2. `test_package/conanfile.py` 同步 `_probe_opencl_runtime()`：消费者冒烟
   测试运行前同样激活真机 OpenCL，保证 test_package 与上游测试行为一致。
3. `notes.md`：本段记录。

**预期**: 若真机确有 OpenCL 实现（vendor ICD 或系统 libOpenCL.so），上游
53 个测试将在真实设备上运行并如实报告通过数；若无，探测日志即「低成本
补齐尝试」的机器证据，测试仍如实失败，由后端判定环境限制。数字始终来自
ctest 真实输出，不硬编码、不伪造。

## 本轮修复 (2026-08-12, 真机预检 compile 失败, OpenCL 平台已激活但测试退出 SEGFAULT)

**真机新证据（attempt-32017 日志）**：低成本补齐探测成功——`LD_PRELOAD
/vendor/lib64/libOpenCL.so` 激活了 HUAWEI 平台（设备 Maleoon 916），探针
`platforms=1 devices=1`。测试**真实执行并通过**：单精度 36 passed、复数单
精度 36 passed、half 36 passed；double/复数 double 因设备无 fp64
（cl_khr_fp64 缺失，double2 未知类型）按上游 tester 设计打印
"All tests skipped: Unsupported precision"（不计失败）。但**每个测试二进制
在全部用例完成后退出时 SEGFAULT**（52/53 失败，仅 retrieve_parameters
通过——它不创建 context/不编译 kernel）；preprocessor 测试 Subprocess
aborted（kComplexDouble 编译 double2 kernel 失败，TestKernel 首个
CompileFromSource 不在 try 块内，异常未捕获）。同时配方 `_run_upstream_ctest`
第 301 行引用未定义的 `opencl_hints` → NameError → HMBS_UPSTREAM_TEST_RESULT
marker 从未打印 → hmbs 看到"发现 0，执行 0"。

**根因分析**：
1. **退出 SEGFAULT**：进程退出时 ProgramCache 静态析构调用 ~Program() →
   clReleaseProgram；OHOS 真机 OpenCL 驱动（/vendor 系统库）在该时刻已
   卸载/资源已回收 → 访问违例。上游 clpp11.hpp 已对 Android/Windows 加守卫
   （注释 "Causes an access violation under Windows or Android when the
   driver is already unloaded"），OHOS 不在其列故崩溃。补丁 0001 把 OHOS
   加入同款守卫（`!defined(__OHOS__)`，与 Android 行为一致，泄漏可接受）。
2. **preprocessor abort**：设备无 fp64，kComplexDouble 的 double2 kernel
   无法编译。补丁 0002 在 RunPreprocessor 开头对不支持的精度直接
   "All tests skipped: Unsupported precision" 返回 0，与 correctness
   tester 的 PrecisionSupported 处理一致（不算失败）。
3. **NameError**：_probe_opencl_configs 返回 (best_env, probe_log)，
   而 marker 代码引用从未赋值的 opencl_hints。修复：从 best_env 提取
   LD_PRELOAD/LD_LIBRARY_PATH/OCL_ICD_VENDORS 构成 opencl_hints。

**本轮工作树改动（未 commit，hmbs 预检通过后统一提交推送）**：
1. `patches/0001-ohos-program-release-guard.patch`：clpp11.hpp ~Program()
   增加 OHOS 守卫，跳过 clReleaseProgram（防退出时访问已卸载驱动）。
2. `patches/0002-preprocessor-unsupported-precision.patch`：
   preprocessor.cpp 跳过设备不支持的精度（无 fp64 时 kComplexDouble）。
3. `conandata.yml`：注册上述两个补丁（patch_type: portability）。
4. `conanfile.py`：_run_upstream_ctest 从 best_env 构建 opencl_hints，
   修复 NameError，保证 marker 正常打印。
5. `test_package/MANIFEST.yml`：审计文本更新为真机已发现 HUAWEI OpenCL
   平台的新证据（53 用例接入执行，fp64 不支持精度按上游设计跳过）。

**预期**：修复后 53/53 ctest 通过（S/C/H 精度真实通过，D/Z 及 preprocessor
的 kComplexDouble 按上游 Unsupported precision 设计跳过，均返回 0）；
marker 打印真实数字 discovered=53 executed=53 passed=53 failed=0。


## 本轮修复 (2026-08-12, 真机预检 upstream_test 失败, half 精度 3 例程失败)

**失败证据（attempt-32247）**：53 用例中 50 过 3 挂，全部集中在 half (fp16) 精度：
- `clblast_test_xamax`：iHAMAX 11/12 失败，误差率恒 1.56% = 2/128
  （amax id1*id2=1，size=1+127=128；imax 索引结果被主循环与 canary 检查
  各计 1 次 → 索引本身与参考不同）。
- `clblast_test_xaxpybatched`：HAXPYBATCHED 39/72 失败，误差率精确
  = 1/(n×batch+127)（n=7→0.75%、n=93→0.45%、n=4096→0.02%），
  每用例恰好 1 个元素不同。
- `clblast_test_xgemmbatched`：HGEMMBATCHED 299 失败，误差率精确
  = 1/(m×n×batch+127)（m=n=k=7→0.57%/0.36%、64×64→0.02%），
  每用例恰好 1 个元素不同。
- 对照：float 精度的 SAMAX/SAXPYBATCHED/SGEMMBATCHED 全过（SGEMMBATCHED
  468 passed/0 failed），非 batched 的 HAXPY/HGEMM、以及
  XGEMMSTRIDEDBATCHED 也全过 → 问题严格限定在 half + batched 内核 +
  amax 参考。

**根因分析（上游 bug，非设备精度问题）**：
1. **iHAMAX 参考实现缺失回写**：test/wrapper_cblas.hpp 的 `cblasXamax`
   half 版把 `imax_buffer` 拷贝到 `imax_buffer_bis` 后调用 float 版，
   但**从不把结果写回 `imax_buffer`** → 参考索引恒为初始垃圾值，
   与 CLBlast 正确索引必然不同 → 必失败。其它 half 包装
   （asum/axpy/gemm/nrm2）都有 FloatToHalfBuffer 回写，唯独 amax 缺失。
2. **batched 内核 alpha/beta 缓冲类型不匹配**：XaxpyBatched /
   XgemmBatched / XgemmDirectBatched* 把 alpha/beta 缓冲声明为
   `__constant real_arg*`；common.opencl 中 PRECISION 16 时
   `real_arg = float`（4 字节/个），而宿主侧写的是 `Buffer<T>`=
   `Buffer<half>`（2 字节/个）→ 内核按 float 读 half 数据，读取错位。
   非 batched / strided-batched 例程用标量 `real_arg`（宿主经
   GetRealArg 转 float 传参，正确），故只有 batched 例程受影响。
   修复：缓冲参数改为 `__constant real*`（half 时即 half*，与
   Buffer<half> 一致；float 时 real=float，行为不变）。

**本轮工作树改动（未 commit，hmbs 预检通过后统一提交推送）**：
1. `patches/0003-amax-half-reference-writeback.patch`（新增）：
   - test/wrapper_cblas.hpp：cblasXamax half 版补 `imax_buffer = imax_buffer_bis;`
   - src/kernels/level1/xaxpy.opencl：XaxpyBatched arg_alphas 改 real*
   - src/kernels/level3/xgemm_batched.opencl：arg_alphas/arg_betas 改 real*
   - src/kernels/level3/xgemm_direct_batched.opencl：4 处
     XgemmDirectBatched* 参数改 real*
2. `conandata.yml`：注册补丁 0003（patch_type: portability）。
3. `notes.md`：本段记录。

**预期**：修复后 iHAMAX 参考返回正确索引、HAXPYBATCHED/HGEMMBATCHED
的 alpha/beta 按 half 正确读取，53/53 ctest 通过
（discovered=53 executed=53 passed=53 failed=0），marker 数字来自
ctest 真实输出，不硬编码。

## 本轮修复 (2026-08-12, 真机预检 compile 失败, test_package build() TypeError)

**失败证据（attempt 日志）**：
```
clblast/1.7.0 (test package): Calling build()
ERROR: clblast/1.7.0 (test package): Error in build() method, line 29
	incs.append(os.path.join(ocl.package_folder, "include"))
	TypeError: expected str, bytes or os.PathLike object, not NoneType
```
即 test_package `build()` 里 `self.dependencies["opencl-headers"].package_folder`
为 None。

**根因**：Conan 2 的 test_package 只直接 require 了 `self.tested_reference_str`
（clblast），而 opencl-headers / opencl-icd-loader 是 clblast 的**传递**依赖。
在 Conan 2 中，`self.dependencies` 对非直接依赖返回的对象 `package_folder`
为 None（主配方 generate() 能正常工作正是因为 opencl-headers 在那里是
**直接**依赖）。test_package 直接拼绝对路径因此 TypeError。

**修复**：test_package `requirements()` 把 opencl-headers/2026.05.29 与
opencl-icd-loader/v2024.05.08 声明为**直接**依赖（版本与主配方一致，Conan
去重不会引入第二份），`package_folder` 即可用，与主配方 generate() 同款。

**本轮工作树改动（未 commit，hmbs 预检通过后统一提交推送）**：
1. `test_package/conanfile.py`：requirements() 新增两个直接依赖 + 注释说明。
2. `notes.md`：本段记录。

**预期**：test_package build() 成功编译 test_clblast 并在真机冒烟运行
（discovered=1 passedCount=1），上游 53 用例继续如实执行。

## 本轮修复 (2026-08-12, 真机预检 test_package build() 链接失败, undefined libc++ symbols)

**失败证据（attempt 日志）**：
```
clblast/1.7.0 (test package): Calling build()
RUN: /data/service/hnp/bin/clang test_clblast.c -o test_clblast ... -lclblast -lOpenCL -lm
ld.lld: error: undefined symbol: __cxa_begin_catch / __cxa_end_catch /
  operator new(unsigned long) / operator delete(void*) / std::terminate() /
  __cxa_allocate_exception / typeinfo for std::length_error /
  __gxx_personality_v0 / std::__n1::* ... (referenced by libclblast.a 内对象)
clang-15: error: linker command failed with exit code 1
```

**根因**：`libclblast.a` 是 **C++** 静态库，归档内对象引用 libc++ 运行时
符号（operator new/delete、__cxa_*、std::terminate、__gxx_personality_v0、
std::__n1:: 命名空间实现等）。test_package 用 **C 驱动 clang** 编译链接
test_clblast.c，C 驱动不会自动带上 libc++，因此全部 undefined。

**修复**：test_package build() 改用 **C++ 驱动 clang++**（从 conan conf
`tools.build:compiler_executables` 取 "cpp"，回退 /data/service/hnp/bin/clang++，
与主配方取 "c" 同款）。clblast_c.h 自带 `extern "C"` 保护，test_clblast.c
按 C++ 编译不影响 C API 符号链接。

**本轮工作树改动（未 commit，hmbs 预检通过后统一提交推送）**：
1. `test_package/conanfile.py`：build() 用 cxx 替代 cc + 注释说明。

**预期**：test_package build() 链接成功（clang++ 自动带 libc++），真机冒烟
运行通过（discovered=1 passedCount=1），上游 53 用例继续如实执行。

## 本轮修复 (2026-08-12, 真机预检 test_package test() 失败, No OpenCL platform found)

**失败证据（attempt 日志）**：
```
clblast/1.7.0 (test package): RUN: /bin/sh -c 'cd "<tmpdir>" && "<...>/test_clblast"'
No OpenCL platform found
ERROR: clblast/1.7.0 (test package): Error in test() method, line 105
```

探针日志显示 `test_package 发现系统 libOpenCL.so: /vendor/lib64/libOpenCL.so`
（LD_LIBRARY_PATH 已前置），但 test_clblast 仍报 "No OpenCL platform found"。

**根因**：test_package 的 `_probe_opencl_runtime` 只设置 `LD_LIBRARY_PATH`，
而 `test()` 里 `self.run(run_cmd, env="conanrun")` 的 conanrun env（由
opencl-icd-loader / openblas 的 runenv 生成）会把 `LD_LIBRARY_PATH` **覆盖**为
依赖包目录，/vendor/lib64 丢失，动态链接器仍加载 conan 的 opencl-icd-loader
libOpenCL.so（ICD loader，无 ICD 文件 → 0 平台），所以枚举失败。主配方
upstream_test 阶段的探针实测（attempt-32017/32247/32322 日志）早已证明
`LD_PRELOAD /vendor/lib64/libOpenCL.so` 才是有效激活方式（platforms=1
devices=1，Maleoon 916）——LD_PRELOAD 不会被 conanrun env 覆盖。

**修复**：test_package `_probe_opencl_runtime` 与主配方 `_probe_opencl_configs`
对齐——优先对系统 libOpenCL.so 设 `LD_PRELOAD`（找到即返回），无系统实现时
才退回 vendor ICD 目录探测（OCL_ICD_VENDORS）。

**本轮工作树改动（未 commit，hmbs 预检通过后统一提交推送）**：
1. `test_package/conanfile.py`：`_probe_opencl_runtime` 改用 LD_PRELOAD
   激活系统 OpenCL 实现（替换原 LD_LIBRARY_PATH 方案）+ 注释说明。
2. `notes.md`：本段记录。

## 本轮修复 (2026-08-12, 真机预检 evidence 失败, 缺少 HMBS_UPSTREAM_TEST_RESULT)

**失败证据（attempt-32407 日志）**：
```
[preflight] conan create 通过
...
======== Installing packages ========
opencl-icd-loader/v2024.05.08: Already installed! (1 of 2)
clblast/1.7.0: Already installed! (2 of 2)
======== Launching test_package ========
...
HMBS_TEST_PACKAGE_RESULT={"executed": true, "passed": true, "discovered": 1, "passedCount": 1, ...}
```
清单器判 incomplete：缺少 HMBS_UPSTREAM_TEST_RESULT（发现 0 执行 0 通过 0）。

**根因**：预检 conan create 用 `--build=missing`；上一轮（attempt-32322）已把
clblast/1.7.0 二进制构建进 conan 缓存，本轮主配方（conanfile.py）内容未变 →
recipe revision 相同（3aaadcda...）→ 缓存命中（"Already installed!"）→ **build()
被跳过**，`_run_upstream_ctest()`（ctest + HMBS_UPSTREAM_TEST_RESULT）根本没执行。
对比 attempt-32322：那轮 build() 真实跑了 ctest，53/53 通过且标记完整输出，但
test_package 因 `CL/opencl.h not found` 失败；后续轮次只改 test_package/conanfile.py
（不进主配方 exports），主配方 revision 不变，故缓存命中、上游标记缺失。

**修复**：本轮修改主配方 conanfile.py（标记打印加 flush=True，对齐 airlift-slice
已验证经验：Conan output 系统在 build 阶段可能不落日志，必须 print(..., flush=True)
直达 stdout）——配方内容变化 → recipe revision 变化 → 预检 conan create 缓存失效
→ 强制重建 → build() 内 ctest 在真机真实执行（53/53，LD_PRELOAD 探针激活
Maleoon 916），HMBS_UPSTREAM_TEST_RESULT 如实输出。Conan 2 已移除
`build_policy="always"`（测试断言 `has been removed`），无法靠该属性强制重建，
配方侧强制重建只能靠 revision 变化触发（与 hmbs「代码内容再次变化时旧验证立即
失效」机制一致）。

**本轮工作树改动（未 commit，hmbs 预检通过后统一提交推送）**：
1. `conanfile.py`：`_run_upstream_ctest()` 中 ctest 输出与 HMBS_UPSTREAM_TEST_RESULT
   标记打印均加 `flush=True`（直达 stdout，绕过 Conan output 缓冲）+ 注释说明。

**预期**：下一轮预检因 recipe revision 变化强制重建 → build() 里 ctest 真实执行
（53/53 passed），HMBS_UPSTREAM_TEST_RESULT 标记输出（discovered=53 executed=53
passed=53），test_package 继续通过（discovered=1 passedCount=1），两标记齐全放行。

**预期**：test_package 冒烟测试在真机 HUAWEI OpenCL 平台（Maleoon 916）上
真实运行 CLBlastSaxpy 并通过（discovered=1 passedCount=1），上游 53 用例
继续如实执行（passed=53）。
