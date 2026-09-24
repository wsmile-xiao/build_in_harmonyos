# vigra 1.12.4 — 编译进度

> 档案创建时间: 2026-09-19
> 最后更新: 2026-09-19
> 申请人: gyccc / 队伍: NebulaAGI
> 适配路径: 路径 A（基础适配）

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | vigra |
| 版本 | 1.12.4 |
| 上游仓库 | https://github.com/ukoethe/vigra |
| 上游版本标签 | Version-1-12-4 |
| 源码 URL | https://github.com/ukoethe/vigra/archive/refs/tags/Version-1-12-4.tar.gz |
| SHA256 | fa516eeb19f72ae98a6d5a284c033bc0e0070cb73a8c72985696d2ad73a9292a |
| 构建系统 | cmake |
| 状态 | built |
| 适配路径 | 路径 A（基础适配） |

## 二、依赖
| 依赖 | 版本 | 说明 |
|------|------|------|
| zlib | 1.3.1.1 | 压缩，必需 |
| libpng | 1.6.58 | PNG 读写 |
| libjpeg-turbo | 3.2.0 | JPEG 读写 |
| libtiff | 4.7.2 | TIFF 读写 |
| fftw | 3.3.10 | FFT 支持 |
| hdf5 | 1.14.4 | 可选，默认关闭 |
| openexr/imath | 3.3.4/3.2.2 | 可选，默认关闭 |
| boost | 1.85.0 | 可选，默认关闭 |
| lemon | 3.53.0 | 可选，默认关闭 |

默认以最小依赖构建（仅前 5 项），其余通过 `with_*` 选项按需开启，避免在 OHOS 上引入重型可选依赖。

## 三、编译要点
- 关闭 vigranumpy (`WITH_VIGRANUMPY=OFF`)：避免 Python/booster 依赖，OHOS 无需 Python 绑定。
- 关闭文档 (`BUILD_DOCS=OFF`)：避免 doxygen 依赖。
- 开启测试 (`BUILD_TESTS=ON`)：触发上游 ctest；本配方最小依赖配置下 `ctest -N` 注册 **53 项**（全选项开启时为 58）；构建阶段执行 `ctest --output-on-failure` 收集真实通过率。
- `VIGRA_STATIC_LIB` 随 `shared` 选项切换；OHOS 默认静态库，避免 .so 污染系统目录（非系统同名库，保留 .so）。
- `WITH_HDF5/OPENEXR/BOOST_GRAPH/LEMON` 默认 OFF，保持与 conan-center 兼容但最小化依赖链。
- 产物签名：复用 libtiff 的 `.so` 重签逻辑（llvm-objcopy 去旧 .codesign + binary-sign-tool -selfSign 1），确保 OHOS dlopen 校验通过。
- 工具链：依赖 Conan profile 提供的 `user_toolchain`（ohos.toolchain.cmake），CMakeToolchain/CMakeDeps 自动注入。

## 四、上游测试审计
- 上游测试入口：`CMakeLists.txt` 中 `option(BUILD_TESTS ...)` 控制 `add_subdirectory(test)`；各子目录 `test/<子目录>/CMakeLists.txt` 通过 `VIGRA_ADD_TEST` 宏注册测试，测试脚本由 `config/VigraAddTest.cmake` 生成。
- 源码盘点（test/CMakeLists.txt 的 63 个 `ADD_SUBDIRECTORY` 逐目录读 CMakeLists，逐条 IF/ELSE 评估）：
  - 在配方构建选项（`WITH_HDF5=OFF`、`WITH_OPENEXR=OFF`、`WITH_BOOST_GRAPH=OFF`、`WITH_LEMON=OFF`、`WITH_VALGRIND=OFF`，`FFTW3_FOUND=true`、`THREADING_FOUND=true`）下注册 **53 个** ctest 条目（`ctest -N` 口径，`ctest_entries`）。
  - 关闭的 5 个：`hdf5impex`(test_hdf5impex)、`polytope`(test_polytope)、`gridgraph`(test_gridgraph_BGL/LEMON)、`objectfeatures`(test_objectfeatures_lemon)。
  - classifier / random_forest_3 / multiarray / registration / simpleanalysis 的 IF(HDF5/THREADING) 分支仅影响链接库，两分支都注册同名测试，故计数不变。
  - 全选项（HDF5/LEMON/BOOST_GRAPH 全开）为 58（Debian/issue 409 日志 `1/58` 至 `58/58`），但非本配方默认口径。
- 统计口径：`ctest_entries`（`ctest -N` 计数）。
- 本次申报：`upstream_test_total: 53`，`upstream_test_count_method: ctest_entries`。
- 运行方式：`conanfile.py` 的 `build()` 中执行 `ctest --output-on-failure`，从 `Testing/Temporary/LastTest.log` / ctest stdout 的 `Test #N` 状态行确定性计数并在真机 OHOS aarch64 上上报 `HMBS_UPSTREAM_TEST_RESULT`。
- 已知不稳定项（历史问题）：`test_blockwiselabeling`/`test_blockwisewatersheds` 在高优化下偶发失败（上游 issue #409），Debian 通过降优化规避；OHOS 上以真实 ctest 输出为准，失败按 `gaps` 机制如实上报，不伪造通过率。
- 若上游测试因缺可选依赖被跳过（如 HDF5 相关用例未构建），不视为 missing_dependency 豁免，属 `ohos_feature`/`environment` 分类并附日志。

## 五、验证结果（待真机预检回填）
- 编译状态：待真机 `conan create` 验证
- 上游测试用例通过率：待真机 `ctest` 输出回填（`HMBS_UPSTREAM_TEST_RESULT` 标记为准）
- 新增测试用例通过率：待真机 `test_package` 输出回填（`HMBS_TEST_PACKAGE_RESULT` 标记为准）

## 六、补充说明
- 适配路径为路径 A（基础适配）：仅完成核心库 `vigraimpex` 的 OHOS 编译与消费者验证，未涉及 Python 绑定或文档生成等创新路径。
- 未修改上游测试源码；测试接入仅通过 `conanfile.py` 的 `cmake.test()` 触发。
- 如真机出现 OHOS 特有失败（如缺 HDF5 导致相关测试未构建），将在 PR 正文 `gaps` 中逐项说明并附日志证据。

## 七、真机修复记录
- 2026-09-21 轮（上游 executed=44, passed=0, failed=44）：count 解析 bug 已在上轮修复；本轮根因是**共享库运行时路径缺失**。
  - 根因：上游测试可执行文件链接依赖的共享库（fftw/libpng/libjpeg/libtiff/zlib 等）。conanfile.py 用裸 subprocess.run(["ctest",...]) 执行，未应用 Conan run 环境（LD_LIBRARY_PATH）。test_package 之所以通过，是因为它走 self.run("./test_vigra", env="conanrun") 注入了 LD_LIBRARY_PATH；主配方 ctest 却没有，测试二进制在加载阶段找不到 .so —— 44 项全部 Failed。
  - 证据：配方内 LDFLAGS 用 -Wl,-rpath-link,<dep lib>（共享库传递链接所需）；存在完整 .so 重签逻辑；test_package 经 conanrun 成功证明该 OHOS 上 LD_LIBRARY_PATH 既必要又充分。
  - 修复：在 ctest subprocess.run 调用注入 env，把每个依赖 lib/ 目录前置到 LD_LIBRARY_PATH（dep_prefixes 已在 build() 内计算好）。若依赖为静态则为无害空操作。
  - 待真机复跑确认：若 44 项由此转绿则验证通过；残留失败按 gaps 如实上报。
- 2026-09-21 轮（再次 44/0/44，LD_LIBRARY_PATH 修复无效果，第 3 次修复）：根因指向 **vigra 单元测试框架 `unittest.hxx` 的 `catch_signals`**。
  - 该函数为 SIGFPE/SIGTRAP/SIGSEGV/SIGBUS 安装 `signal()` 处理器，处理器内 `longjmp()` 回到 `catch_signals` 里 `setjmp()` 的**另一栈帧**（跨 `function_object()`）。在 OHOS musl/aarch64 上这是 UB，导致所有使用该框架的执行（53 个上游测试全部）行为异常 → 全 Failed；而 test_vigra 是普通 main+assert 不经过框架，故通过。
  - 修复：在 `conanfile.py` 的 `source()` 里向 `vigra/config.hxx` 注入 `#define VIGRA_CANT_CATCH_SIGNALS`（上游自己为 Cygwin/非 UNIX 保留的移植路径），使 `catch_signals` 直接 `return function_object()`，用例走普通 try/catch 真实执行断言，不装信号处理器、不 longjmp。
  - 另在 marker 增加 `reason`（首个失败用例的实况输出摘录）作诊断，便于下轮确认/纠正。
  - 这是最合理举证（framework vs 普通消费者差异）后的针对性尝试；究竟是否命中由下轮真机判定。
- 2026-09-22 轮（再次 44/0/44，`./test_XXX: inaccessible or not found`，第 4 次修复）：**真根因确认——上游测试可执行文件根本没被构建**。
  - 根因：VIGRA_ADD_TEST 里 `IF(AUTOBUILD_TESTS) ADD_EXECUTABLE(...) ELSE() ADD_EXECUTABLE(... EXCLUDE_FROM_ALL ...) ENDIF()`，而 `AUTOBUILD_TESTS` 默认 **OFF**（VigraSetDefaults.cmake）；每个测试 target 只通过 `ADD_DEPENDENCIES(check_cpp ${target})` / `ADD_DEPENDENCIES(ctest ${target})` 挂到 `check_cpp`/`ctest` 自定义 target，**不进默认 `all`**。conanfile 只执行 `cmake --build <bdir>`（默认 all 目标），导致 53 个 test_* 二进制从未编译 → `run_test_*.sh` 里 `cd <binary_dir> && ./test_XXX` 报 `inaccessible or not found`。
  - 证据：upstream `config/VigraAddTest.cmake`（EXCLUDE_FROM_ALL 分支 + check_cpp/ctest 依赖）与 `config/VigraSetDefaults.cmake`（AUTOBUILD_TESTS=OFF）；日志 `run_test_correlation.sh[2]: ./test_correlation: inaccessible or not found` 是脚本第 2 行，正是 `cd ... && ./test_correlation`。
  - 前两轮（LD_LIBRARY_PATH、VIGRA_CANT_CATCH_SIGNALS）都是对"二进制已存在"症状的猜测，实际二进制从未生成，故从未进入共享库加载/信号处理器路径；这两项无害但非本轮根因。
  - 修复：
    1) configure 增加 `-DAUTOEXEC_TESTS=OFF`——否则 `--target check_cpp` 时每个测试 targe 的 POST_BUILD 会在无 Conan run env（无 LD_LIBRARY_PATH）下自动执行测试脚本，加载共享依赖失败会中止整个构建；
    2) `cmake --build <bdir> --target check_cpp` 显式构建全部测试二进制（该自定义 target 依赖每个 test target、无 COMMAND，只编译不运行），随后照旧执行 `ctest --output-on-failure`（该步已带 LD_LIBRARY_PATH）。
  - 保留上轮 LD_LIBRARY_PATH 注入（二进制真正存在后，运行阶段仍需找 conan cache 的 .so）+ VIGRA_CANT_CATCH_SIGNALS（若框架问题存在，留作证据）。是否全绿由下轮真机判定，残留真实失败按 gaps 如实上报。

- 2026-09-22 轮（`--target check_cpp` 链接 test_correlation 失败，fftwf_* 未定义符号，第 5 次修复）：
  - 根因：test_correlation 是唯一使用单精度 FFTW3F 的上游测试。`test/correlation/CMakeLists.txt` 用
    `VIGRA_ADD_TEST(test_correlation ... LIBRARIES ${FFTW3_LIBRARIES} ${FFTW3F_LIBRARIES} ...)`
    注册，且只被 `if(FFTW3_FOUND)`（双精度）守卫；test.cxx 无条件引用 `fftwf_*` 单精度符号。
    配方只设置了 `FFTW3_*` 缓存变量，未设置 `FFTW3F_*`，导致 vigra 的 FindFFTW3F 找不到库 →
    `${FFTW3F_LIBRARIES}` 为空 → 链接仅带 `-lfftw3`（双精度）却引用 `fftwf_destroy_plan`/
    `fftwf_plan_many_dft_r2c`/`fftwf_plan_many_dft_c2r`/`fftwf_execute_dft_r2c`/
    `fftwf_execute_dft_c2r` → ld.lld undefined symbol。
  - 证据（真机日志）：configure 段 `-- Could NOT find FFTW3F (missing: FFTW3F_LIBRARY FFTW3F_INCLUDE_DIR)`；
    链接命令行 `... -lfftw3 -lm` 后 `ld.lld: error: undefined symbol: fftwf_destroy_plan`（referenced by test.cxx，
    defined in libfftw3.so，did you mean fftw_plan_many_dft_r2c）。
  - 修复：同一 fftw conan 包（`--enable-shared` 默认构建双/单/长双三种精度）内含单精度 `libfftw3f.so`，
    在配方 build() 中为 FFTW3F 显式写入缓存变量：
    `-DFFTW3F_INCLUDE_DIR=<fftw include>`、`-DFFTW3F_LIBRARY=<libfftw3f.so>`、
    `-DFFTW3F_LIBRARIES=<libfftw3f.so>`，使 FindFFTW3F 命中单精度库。
  - 其余上游测试（fourier/filter 等）仅用双精度 FFTW3，不受影响；是否全绿由下轮真机判定。

- 2026-09-22 轮（`--target check_cpp` 链接 test_correlation 报 `No rule to make target .../libfftw3f.so`，第 6 次修复）：
  - 根因（本轮聚焦）：上一轮误判“fftw conan 包内含单精度 libfftw3f.so”。实际 fftw 3.3.10 配方
    （archives/f/fftw/3.3.10）generate() 只 `--enable-shared/--disable-static/--disable-fortran/--disable-doc`，
    **没有 `--enable-single`，唯一产物是双精度 libfftw3.so，根本没有 libfftw3f.so**。
    上一轮 lib_candidate() 的 fallback（“找不到就返回 names[0] 路径”）在文件不存在时仍返回
    不存在的绝对路径 `.../p/lib/libfftw3f.so`，注入 `-DFFTW3F_LIBRARY` 后 CMake 把该不存在路径
    记为链接目标 → `make --target check_cpp` 报 `No rule to make target .../libfftw3f.so` 中止。
  - 证据（真机日志）：`make[3]: *** No rule to make target '.../conan-home/p/fftw02b9874643912/p/lib/libfftw3f.so',
    needed by 'test/correlation/test_correlation'`；且 fftw 3.3.10 conanfile 无 --enable-single。
  - 修复：
    1) `source()` 新增对 `test/correlation/CMakeLists.txt` 的补丁：把 `if(FFTW3_FOUND)` 改为
       `if(FFTW3_FOUND AND FFTW3F_FOUND)`。单精度 FFTW 在本依赖下根本不提供，故 FFTW3F_FOUND 恒 False，
       test_correlation 被诚实排除（不再“注一个空 FFTW3F_LIBRARIES 去链未定义 fftwf_* 符号”，也不再注入
       不存在的库路径）。
    2) `build()` 中 FFTW3F 缓存变量改为**仅当 libfftw3f 真实存在时才注入**（不存在则只打 diag 日志），
       杜绝 lib_candidate 返回不存在的 fallback 路径被写成链接目标的回归。
    3) 上游标记新增 `gaps:[{count:1, category:"ohos_feature", detail:"单精度 FFTW libfftw3f 在 OHOS
       fftw 依赖中不提供，test_correlation 被排除", ...}]`，与 MANIFEST 声明总数 53 对齐（53-通过数=1）。
  - 说明：若未来 fftw 依赖改为提供单精度（--enable-single），本补丁自动失效（FFTW3F_FOUND 会为 True，
    守卫失效、缓存变量注入生效，test_correlation 恢复构建），无需人工改回。
  - 是否全绿由下轮真机判定；test_correlation 以 ohos_feature gap 如实上报，不伪造通过。


- 2026-09-22 轮（rule4：gaps 覆盖 1 项但实际缺口 13 项，本错误指纹第 2 次修复）：
  - 真机数据：discovered=52, executed=43, passed=40, failed=3, skipped=0；声明总数 N=53。
  - 根因：① 配方只上报 test_correlation 一个 ohos_feature gap，未覆盖 3 个真实失败
    （test_failure）与 executed<discovered 的 9 个未执行用例，Σgaps.count=1 != N-passed=13，
    rule4 拒。② executed=43 < discovered=52 说明上轮无 per-test timeout 的 `ctest --output-on-failure`
    在某用例挂起/拖慢时吃满 600s 子进程预算被截断，9 个注册用例从未产出状态行。
  - 修复（区别前次策略：不再只放 1 个写死的 gap，改动态补全）：
    1) ctest 命令加 `--timeout 120`（每用例独立限时，挂死用例被掐后剩余用例继续执行，
       使整套 run 完成、executed==discovered），子进程超时放宽到 1200s；payload command 同步更新。
    2) `_hmbs_parse_per_test` 状态词增补 Timeout 并计入 failed（真实非通过）。
    3) 新增 `_hmbs_parse_per_test_names`（取每用例名称->状态）与 `_hmbs_parse_registered_names`
       （ctest -N 取注册名），据此命名 failed 与 not-run 用例。
    4) gaps 改为动态组装：test_correlation(ohos_feature,1) + 每个失败用例(test_failure,count=1)
       + 未执行用例(environment,count=discovered-executed)；随后自检 Σgaps.count==N-passed，
       不匹配仅告警不伪造数字。
    5) status 语义：仅在 passed 但有 skipped/gaps 时置 incomplete（保持 failed 表示真实失败）。
  - 是否放行由下轮真机 rule4 判定；若 --timeout 生效则 executed==discovered=52，gaps=1+3=4
    == 53-(52-3)=4，自洽。残留 3 个真实失败按 test_failure 如实上报，不删除断言/不伪造通过。
