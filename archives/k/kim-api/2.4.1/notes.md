# kim-api 2.4.1 适配笔记（HarmonyOS PC · CMake）

## 上游信息

- 名称：kim-api（Open Knowledgebase of Interatomic Models API）
- 版本：2.4.1（2025-04-15 发布；2.4.x 系的中间版本，最新为 2.4.2）
- 上游仓库：https://github.com/openkim/kim-api（tag v2.4.1）
- 官方源码包：https://s3.openkim.org/kim-api/kim-api-2.4.1.txz（INSTALL 指定的官方渠道）
- SHA256：`225e3136d43e416a4424551e9e5f6d92cc6ecfe11389a1b6e97d6dcdfed83d44`（364020 字节，已本地下载核验）
- 许可证：LGPL-2.1-or-later
- 构建系统：CMake ≥ 3.10，`project(... LANGUAGES CXX C Fortran)`，默认 `KIM_API_BUILD_EXAMPLES=ON`

## 上游测试审计（结论：33 个 ctest 注册用例，仅 EXAMPLES=ON 可见）

2026-09-29 预检 evidence 门禁驳回旧的 `no_tests` 申报
（"清单表明上游存在测试"），复核上游 v2.4.1 源码后纠正：

- 顶层 `CMakeLists.txt` 仅 `enable_testing()`、全树无裸 `add_test()`，
  但 `examples/simulators/CMakeLists.txt` 经 `add_kim_api_test()`
  （`add_test` 封装，`set_tests_properties(... WILL_FAIL TRUE)` 佐证其为
  真实 CTest 用例）注册 **33** 个用例，仅当 `KIM_API_BUILD_EXAMPLES=ON`
  时进入构建：
  - `_add_simulator_tests`：`Run_collections-example{,-c,-fortran}` 3 个；
  - `_add_simulator_model_tests`：9 个模型的 `_test_models` 列表 x
    `ex_test_Ar_fcc_cluster{,_cpp,_fortran}` 3 变体 = 27 个，其中
    `ex_model_Ar_P_Morse_MultiCutoff` 与 `ex_model_Ar_SLJ_MultiCutoff`
    x 3 变体共 6 个带 `WILL_FAIL TRUE`（ctest 按 Passed 计）；
  - `Run_simulator-model-example{,-c,-fortran}` 3 个；
  - `utility_forces_numer_deriv` 子目录只构建可执行文件、不注册用例。
- 因此 `upstream_test_total=33`（口径 `ctest_entries`，即 `ctest -N` 的
  `Total Tests`），`upstream_tests_exist=true`。旧的"零注册测试"结论仅在
  `KIM_API_BUILD_EXAMPLES=OFF` 下成立，该开关会隐藏整个上游套件，不可取。
- 上游 CI（`scripts/ci-build-and-test` 的 `TEST_BUILD` 段）同样以
  `ctest --output-on-failure` 为门（`|| exit $?`），与本配方一致；
  `TEST_CM`/`TEST_INSTALL_INSTRUCTIONS` 另有需联网（openkim.org 模型下载）
  的集合管理验证，不在 ctest 口径内、不计入总数。

## 构建设计

- Fortran 编译器：HarmonyOS 不自带 Fortran 编译器（知识库 E109），复用已发布
  的 `flang-ohos/20.1.0`（LLVM Flang，openblas/acepack 已验证的同一方案），
  以 `tool_requires` 引入，`CMAKE_Fortran_COMPILER` 指向其 `bin/flang`。
- `KIM_API_BUILD_EXAMPLES=ON`（上游默认为 ON，本配方保持 ON：
  示例子目录承载全部 33 个上游 ctest 用例；曾因真机 compile 阶段 Signal 9
  短暂设为 OFF，但后续同图构建曾达 93%，且 OFF 会隐藏整个套件导致
  evidence 门禁驳回，故恢复 ON 并在 hmbs jobs=1 下实测；若再遇 OOM 则按
  gaps 如实申报，不隐藏套件）：
  核心 `cpp/src + c/src + fortran/src` 与示例三语言目标照常编译。
- 非系统同名库，保留上游的共享库形态（`libkim-api.so.2`），不做 R26 静态强制。
- 头文件安装到 `include/kim-api/`，`package_info()` 同时暴露 `include` 与
  `include/kim-api`；CMake 包名 `KIM-API`、目标 `KIM-API::kim-api`、
  pkg-config 名 `libkim-api`，均与上游安装的配置文件一致。
- 无补丁（`patches_applied: []`）。

## 依赖边界

- 运行/构建依赖：无（纯 CMake + 系统编译器 + flang 工具包）。
- 工具依赖：`flang-ohos/20.1.0`（tool_requires，HDF5 那类缺依赖问题不适用，
  Fortran 由工具包补齐，无需跳过任何上游测试）。

## 测试清单

新增 2 个安装包消费者测试（均真实调用库 API，非空壳）：

1. `kimapi_semver_contract`（test_semver.c）：`KIM_SEM_VER_GetSemVer` 非空且
   包含 `2.4.1`；`ParseSemVer("2.4.1")` 得 2/4/1；非法版本串返回错误；
   `IsLessThan("2.4.0","2.4.1")` 为真、反向为假。共 9 个检查点。
2. `kimapi_collections_contract`（test_collections.c）：`KIM_Collections_Create`
   / `Destroy` 生命周期；`KIM_Log_Create` / `Destroy` 生命周期。共 7 个检查点。

## 真机失败修复（2026-09-29 预检 compile 失败，Signal 9，第三轮·换驱动）

- 现状比较：第二轮的显式串行（`CMAKE_BUILD_PARALLEL_LEVEL=1` +
  `cmake.build --parallel 1/-j1`）与内存瘦身（`-g0 -fno-lto`、section-GC、
  lld `--no-keep-memory`）已在树内，但本轮以完全相同的指纹复现
  （compile 期 Signal 9、空 stdout/stderr、上游 0/0/0）。按防重复要求不得
  原样重复已失败的修改，本轮改动必须与之正交。
- 新根因定位：`CMakeToolchain` 默认生成器为 Unix Makefiles，在 OHOS 上每个
  TU 编译与每次链接都要 fork `/bin/sh`（知识库 E346；OHOS 无原生 `/bin/sh`，
  靠 HMBS 注入 `SHELL=/bin/sh` 兜底）。即使 `-j1`，驱动常驻内存 + 逐 TU 的
  shell fork 峰值仍先触顶 cgroup；上一轮只压了编译器/链接器单进程 RSS，
  没动驱动层开销。rnp/0.18.1 #14 在同指纹下以 Ninja + `-j1` 收敛，
  与本轮失败域一致。
- 本轮修复（仅驱动层，源码/优化等级/测试口径/EXAMPLES=ON 全部不变）：
  `generate()` 中按 `HMBS_NINJA` → `user.hmbs:ninja_path` →
  `PATH which("ninja")` 顺序探测，`--version` 存活才设
  `tc.generator="Ninja"` + `CMAKE_MAKE_PROGRAM` 绝对路径
  （zbackup/aws-lc-tools/intx/gromacs 同式），否则回落默认生成器，
  Linux/CI 行为不变。Ninja 直接 spawn 编译器、无 shell 中介，
  且 `cmake.build --parallel 1` 语义保持串行。
- 边界：若下轮仍同指纹失败，则证峰值不在驱动 fork 而在单个 flang
  `-O3` TU 或单体示例链接，届时再沿 Fortran 降优或示例目标分片方向走，
  不在本轮预支优化等级改动。

## 真机失败修复（2026-09-29 预检 compile 失败，Signal 9，第二轮）

- 现象：预检在 compile 阶段被 SIGKILL（Signal 9），stdout/stderr 尾部均为空，
  上游测试 0/0/0，无编译器错误行。空日志 + SIGKILL 是共享真机 OOM killer 的
  典型签名（rnp/0.18.1 #16 同指纹），不是配方语法错误。
- 根因：hmbs 注入的 `tools.build:jobs=1` 未被显式钉死到构建驱动，
  配方 `cmake.build()` 无参数（默认并行），链接期 lld 多线程/fork 峰值仍可
  触顶 cgroup；Release `-O3` 默认带调试信息与 LTO，进一步推高单进程 RSS。
- 修复（内存瘦身，优化等级/源码/测试口径不变；tmx/1.10.1 + rnp/0.18.1 +
  lammps/uvw 先例）：
  主配方与 test_package 均显式串行（`CMAKE_BUILD_PARALLEL_LEVEL=1` +
  `cmake.build(cli_args=["--parallel","1"], build_tool_args=["-j1"])`）；
  OHOS 分支追加 `-g0 -fno-lto -ffunction-sections -fdata-sections`（Fortran 仅
  `-g0`，保前端兼容）与 `-Wl,--no-keep-memory -Wl,--gc-sections
  -Wl,--exclude-libs,ALL -Wl,--as-needed`（加法追加，Fortran 运行时闭包保留）。
  `KIM_API_BUILD_EXAMPLES=ON` 保持（33 用例套件不隐藏，缺口走 gaps 申报）。

## 真机失败修复（2026-09-29 预检 compile 失败，Signal 9）

- 现象：预检在 compile 阶段被 SIGKILL（Signal 9），stdout/stderr 尾部均为空，
  无编译器错误行。hmbs 已注入 `tools.build:jobs=1`（串行），串行下仍被 kill
  是典型的真机内存不足（OOM killer）签名，而非配方语法错误。
- 上游 `CMakeLists.txt` 在 `KIM_API_BUILD_EXAMPLES=ON` 时额外增加
  `examples/model-drivers + portable-models + simulator-models + simulators`
  四个子目录的全部演示目标（每个都是链接刚构建 lib 的独立 C/C++/Fortran
  目标），构建图规模约翻倍；flang/clang 在 Release `-O3` 下单进程内存本就偏高。
- 修复（已作废，被 evidence 门禁否决）：曾短暂设 `KIM_API_BUILD_EXAMPLES=OFF`，但 OFF 会隐藏全部 33 个上游 ctest 用例导致 evidence 门禁驳回（"清单表明上游存在测试"），故恢复 ON 并在本轮改用串行 + 内存瘦身承接，缺口走 gaps 申报。示例是 INSTALL D.1 定义的交互式演示
  （`printf "model" | ./simulator`），不是自动化测试，也不是安装交付物；
  关闭后核心库三语言源码照常编译（语言覆盖不丢），与 Box2D
  `BOX2D_BUILD_TESTBED=OFF` 保留单测、关闭图形演示的先例一致。
  交付库优化等级不变，不降低、不改测试口径。

- 现象：`cmake.configure()` 在 `project(... C CXX Fortran)` 处失败，
  Fortran 检测 `bin/flang - broken`，`ld.lld: cannot open Scrt1.o/crti.o/
  crtbeginS.o`、`unable to find -lm/-l:libunwind.a`、
  `cannot open .../libclang_rt.builtins.a`。根因是 flang-ohos 为前端精简包，
  裸链接必然失败（lapack/3.12.1、packmol/21.2.3、DRAFT-flang 契约已实证）。
- 修复（仅 OHOS 分支，Linux 行为不变）：
  `CMAKE_Fortran_FLAGS` 注入 `--target/--sysroot/-resource-dir`；
  EXE/SHARED/MODULE linker flags 注入 `-L<sdk>/aarch64-linux-ohos
  -L<sdk>/lib -L<flang>/lib -lFortranRuntime -lFortranDecimal -lm`；
  `CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY` 使编译器检测只编不链；
  `build()` 导出 `LD_LIBRARY_PATH=<sdk>/lib:<flang>/lib`；
  `package()` 捆绑两份 Fortran 静态运行时，静态包消费者自动链接闭包。

## 真机失败修复（2026-09-29 预检 compile 失败，flang 报 Only -std=f2018 is allowed）

- 现象：预检在 compile 阶段失败（165/272），`simulator-model-example-fortran`
  的 flang 预处理命令携带 `-std=gnu`，报错
  `error: Only -std=f2018 is allowed currently`，ninja 停工。
  此前 `fortran_support_for__std_f2003/-Wall/-Wextra/-Wimplicit_interface/-pedantic`
  探测全部 Failed，说明上游 `DefaultCompilerFlags` 的探测分支已被正确过滤，
  残留的 `-std=gnu` 必来自绕过探测的硬编码。
- 根因：`examples/simulators/simulator-model-example/CMakeLists.txt` 硬编码
  `target_compile_options(${PROJECT_NAME}-fortran PRIVATE "-std=gnu")`
  （gfortran GNU 扩展开关，不经过 `check_fortran_compiler_flag` 探测）；
  而真机 Fortran 编译器是 `flang-ohos/20.1.0`（LLVM 20 flang-new），
  只接受 `-std=f2018`。另核查 `collections-example`、
  `ex_test_Ar_fcc_cluster_fortran`、Fortran portable-model
  （`ex_model_Ar_P_MLJ_Fortran`）均无同类硬编码，本轮失败域为单文件单标志。
- 修复（`source()` 内无条件源码树横扫，Spack nvhpc 同式只删标志）：
  遍历 `CMakeLists.txt`/`*.cmake`，把携带 `-std=gnu` 的整条
  `target_compile_options` 语句替换为注释（避免残留 `PRIVATE ""` 空参数），
  其他上下文残留则做裸 token 删除；每个命中记 `kim-api: stripped -std=gnu`
  日志。无条件而非 OHOS 门控：conan source 缓存跨配置共享，条件补丁与下载
  顺序相关；且 gfortran 默认即 GNU 模式，删除对其是 no-op，Linux/CI 行为不变。
- 边界：若下轮出现新的 flang 不兼容标志，按同样方式逐个剥离并记录，
  不预支扩大到整个 Fortran 标志集。

## 证据状态（2026-09-29 evidence 修复轮，未提交）

- 本轮为未提交工作树：配方与测试已按 evidence 门禁要求改完，待真机复检。
- `manifest.yaml` 状态暂标 `built`（待真机实测；绝不标 `published`）。
- 上游 33 用例接入方式：`build()` 中 `_run_upstream_ctest()` 真实执行
  `ctest --output-on-failure`（`ctest -N` 取 discovered，逐行解析
  `Test #N ... Passed|Failed` 取 executed/passed/failed，汇总行与
  `LastTest.log` 仅作一致性见证；failed>0 或见证不一致则抛错，
  零失败但未满总数则标 failed 带 environment gaps 且放行产物）。
  构建树示例可执行文件先经 `binary-sign-tool` 自签名（HongMeng 对无签名
  执行 SIGKILL），载荷持久化至 `res/hmbs_upstream.json` 供缓存轮转文中
  `test_package` 转发（zydis 方案）。
- 测试计数以真机预检日志为准，PR 正文数字待 evidence 轮回填，本轮不猜测。
- 已知待真机验证的风险点：示例全图在受限真机上的内存（曾 Signal 9 一次，
  后续同图达 93%，本次 jobs=1 下复测）；构建树 `sh -c` 测试命令对真机
  `sh` 的依赖；Fortran 示例链接的运行时闭包。

## 真机失败修复（2026-09-29 预检 compile 失败，Fortran 示例缺 CRT Scrt1.o/crti.o/crtn.o）

- 现象：272 目标中 265/272 处 collections-example-fortran 链接失败，flang 命令含 --target=aarch64-linux-ohos -resource-dir=.../Cellar/ohos-sdk/26.0.0.18_1/native/llvm/lib/clang/15.0.4 但无 --sysroot，ld 报 cannot open Scrt1.o/crti.o/crtn.o。
- 根因：SDK 探测 glob 只覆盖 .../ohos/native/llvm，而本容器 SDK 为 .../Cellar/ohos-sdk/<ver>/native/llvm（无 ohos 段，-L 行可证），故 sdk_llvm=None；回退的 clang 查询中 --print-sysroot 为空，配方按原逻辑不注入 --sysroot，导致 flang 裸链找不到 sysroot/usr/lib 下的 CRT。
- 修复（仅 OHOS Fortran 标志推导，不改源码/优化/测试口径）：globs 增补 .../Cellar/ohos-sdk/*/native/llvm 三条；_expand/_derive 支持 native/llvm 与 ohos/native/llvm 双标记；新增 _derive_sysroot_from_known 从 resdir/-L/exe 实路径推导 sibling native/sysroot（存在且含 usr/lib 才接受）；clang-query 分支与 _query_clang_sdk 尾部在 sysroot 为空时自动补齐并追加 sysroot usr/lib 到 -L。

## 真机失败修复（2026-09-29 预检 ctest 6/46 通过，40 失败·运行时闭包）

- 现象：构建 272 目标完成，`ctest -N` 发现 46 个用例（非旧审计的 33），
  `ctest --output-on-failure` 仅 6 通过、40 失败（13% passed）。
  通过的 6 个恰为 `WILL_FAIL TRUE` 的 MultiCutoff 预期失败用例
  （ctest 对“失败符合预期”计 Passed）；全部 40 个应通过用例在
  0.03~0.06 秒内失败。秒级全灭 + 预期失败全“过”是典型的构建树
  测试二进制启动期装载失败签名（E019 同系），而非 40 个模型各自的
  数值/物理失败。
- 根因（构建树运行时库路径缺失，rnv/1.7.11 同类）：ctest 直接执行
  构建树示例可执行文件，它们链接刚构建的 `libkim-api.so`；
  OHOS 上该构建树 RPATH 不可靠，配方此前只在 `build()` 前半段导出
  `LD_LIBRARY_PATH`（flang/sdk），但未把含 `libkim-api.so*` 的构建树
  目录显式前置到 ctest 子进程环境。子进程（含 `sh -c` 孙进程）装载期
  找不到 `libkim-api.so` 即退，WILL_FAIL 用例因“失败符合预期”反而计 Passed。
- 修复（仅 OHOS ctest 环境，不改源码/优化等级/测试口径）：
  `_run_upstream_ctest()` 在 ctest 前动态收集含 `libkim-api.so*` 的
  构建树目录 + `build/` + `build/lib` + flang `lib` + SDK llvm `lib` /
  clang 查询 `lib_dirs`，全量前置为 `LD_LIBRARY_PATH` 并打日志；
  `sh -c` 测试经继承自动生效。另在失败时转储前 3 个失败用例的
  `LastTest.log` 段尾（各 30 行），使下轮有精确失败域（装载错误 vs
  模型错误），计数仍只来自 `ctest -N` + 逐行 `Passed|Failed` 单一来源。
- 口径修正：`ctest -N` 真机实测 46（33 simulator 运行 + 13
  `shared_library_test_*` 构件检查），MANIFEST/配方注释/草稿正文中的
  旧“33”同步为 46。`test_package/MANIFEST.yml` 审计已增补 item 侧 13
  用例的日志证据；上游/新增断言与测试命令不变。
- 边界：若下轮 `LastTest.log` 段尾显示 `cannot open shared object` 以外
  的错误（如模型 dlopen 缺符号、HOME/写权限、toybox `sh` 语义），
  则按新证据另起失败域处理，不再动 `LD_LIBRARY_PATH`。

## 真机失败修复（2026-09-30 预检 ctest 45/46，1 失败·Fortran 整数组赋值越界）

- 现象：上轮运行时闭包修复后 45/46 通过，仅剩
  `Run_collections-example-fortran` 失败（0.18 秒，Signal 6），
  `LastTest.log` 段尾（本配方失败转储机制生效）给出精确定位：
  `fatal Fortran runtime error(.../fortran/include/kim_collections_module.f90:638):
  Assign: mismatching element counts in array assignment (to 10000, from 39)`。
  C/C++ 版 collections-example 均通过，只有 Fortran 版失败。
- 根因（上游库代码违反 Fortran 整数组赋值一致性，flang-new 严格执行）：
  上游示例 `collections-example-fortran.f90` 声明 10000 字节的
  `file_raw_data(10000)` 缓冲并传入
  `kim_get_item_metadata_file_values`；库函数在
  `kim_collections_module.f90:638` 执行整数组赋值
  `file_raw_data = file_raw_data_fpointer(1:file_length)`（file_length=39）。
  整数组赋值要求形状一致，39 元赋给 10000 元属非 conforming 代码；
  gfortran Release 构建静默只写前导元素（上游 CI 用 gfortran 故常绿，
  v2.4.2 对比确认上游未改此代码），而 flang-new（flang-ohos/20.1.0，
  LLVM 20）运行时直接 abort。同文件第 1031 行（by_collection 变体）与
  `kim_model_module.f90` 的 `cutoffs`（638 行）及
  `model_will_not_request_neighbors_of_noncontributing_particles`
  （657 行）三处同构写法是同一潜伏 bug，共 4 处。
- 修复（`source()` 内精确改写，不改测试、不删断言、不跳过）：
  把 4 处 LHS 改写为显式 `(1:n)` 段（`file_raw_data(1:file_length) = ...` 等），
  每处上游均有 `size(...) < n -> ierr=1` 守卫先行，故改写后恒 in-bounds；
  gfortran 下可观察行为不变（原本就只写前 n 个），flang 下不再 abort。
  精确匹配 + 合计 4 命中断言（对真实 v2.4.1 文本 dry-run 验证为 4/4），
  上游布局漂移时大声失败而非静默半修。无条件执行（与 -std=gnu 同理，
  conan source 缓存跨配置共享）。这不是测试豁免：46 个用例全部继续真实运行。
- 边界：若下轮出现新的 flang 运行时 abort，按同样方式逐个修库代码并记录；
  file_length=0 的空段赋值是合法 no-op，不引入新风险。
