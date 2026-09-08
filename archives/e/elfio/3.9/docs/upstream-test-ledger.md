# ELFIO 3.9 上游测试完整枚举台账（R03 更新版）

- 任务: elfio-3.9-r03-boost-1.90.0.2.1-upstream-test-recovery-pc3-7-20260905T064500Z
- 上游来源: https://github.com/serge1/ELFIO (tag: Release_3.9)
- 官方 release 包: elfio-3.9.tar.gz (SHA-256 767b269063fc35aba6d361139f830aa91c45dc6b77942f082666876c1aa0be0f)
- 枚举依据: git tag Release_3.9 完整 tree（271 路径，GitHub API `git/trees/Release_3.9?recursive=1`）

## 0. R03 Boost 依赖复核结论（本轮新增）

- 注册表核验: `conan list 'boost/1.90.0.2.1' -r=ohpcd` → **存在**（canonical reference: boost/1.90.0.2.1，
  revision 80804a28，包 id 01d92cf349a0dd98ff915f4bd99a04430171517f，revision 46ff9a49）；未替换为 boost/1.84.0。
- 下载核验: `conan download 'boost/1.90.0.2.1' -r=ohpcd`（含 --only-recipe 与完整包）→ dl_rc=0。
- 包内容核验: 包 include/boost 顶层 195 条目；**无 boost/test 目录**；`boost/test/unit_test.hpp` 与
  `boost/test/included/unit_test.hpp` 均不存在；recipe 无 `unit_test_framework` 组件/CMake target 定义。
- 真实编译尝试: `clang++ -std=c++17 -I<boost 包 include> -I<src> ELFIOTest.cpp ELFIOTest1.cpp ELFIOTest2.cpp -o ...`
  → 首错 `fatal error: 'boost/test/included/unit_test.hpp' file not found`（ELFIOTest.cpp:28）与
  `'boost/test/unit_test.hpp' file not found`（ELFIOTest1.cpp:28 / ELFIOTest2.cpp:28），compile_rc=141。
- **结论**: boost/1.90.0.2.1 注册表可用但**包内不含 Boost.Test 头** → 36 上游用例仍硬阻塞，
  属真实外部依赖/包内容阻塞（非本库配方或源码缺陷）。证据日志: evidence/boost_dependency_audit.log。

## 0b. R04 运行结果（本轮新增，boost/1.90.0）

- 依赖变更: 任务指定改用 `boost/1.90.0`（R03 已证 1.90.0.2.1 缺 Boost.Test 头，未替换）。
  - `conan list 'boost/1.90.0' -r=ohpcd` → 存在（canonical boost/1.90.0，revision f91a3513655305557522653755146736）。
  - `conan download 'boost/1.90.0' -r=ohpcd`（recipe + 完整包）→ dl_rc=0。
  - 包内容: include/boost 顶层含 **boost/test 目录**；`boost/test/included/unit_test.hpp` 与
    `boost/test/unit_test.hpp` 均存在；recipe 定义 `unit_test_framework` 组件（CMake target
    `Boost::unit_test_framework`）；`libboost_unit_test_framework.a` 存在。
- 构建: `clang++ -std=c++17 -I<boost include> -I<src> -I<tests> ELFIOTest.cpp ELFIOTest1.cpp
  ELFIOTest2.cpp -L<boost lib> -lboost_unit_test_framework -o ELFIOTest` → **compile_rc=0**。
- 运行: `./ELFIOTest --report_level=detailed`（cwd=运行目录，含 elf_examples 54 fixture）
  → **run_rc=0；36/36 用例全部通过，0 失败；汇总断言全过**。
  完整日志: evidence/upstream_test_full_r04.log（SHA-256 86852aba…），
  运行摘要: evidence/upstream_test_run_r04.log（SHA-256 67bc9d3e…）。

## 1. 枚举范围与分类

| 类别 | 入口 | 独立用例数 | 分类理由 |
|------|------|-----------|---------|
| 用户测试源 | tests/ELFIOTest.cpp | 13 | BOOST_AUTO_TEST_CASE，真实用户用例 |
| 用户测试源 | tests/ELFIOTest1.cpp | 16 | BOOST_AUTO_TEST_CASE，真实用户用例 |
| 用户测试源 | tests/ELFIOTest2.cpp | 7 | BOOST_AUTO_TEST_CASE，真实用户用例 |
| 框架头/源码 | Boost unit_test_framework（`boost/test/included/unit_test.hpp`、`boost/test/unit_test.hpp`） | 0 | 测试框架，非用户用例 |
| 样例 | examples/（writer、elfdump、anonymizer、add_section、write_obj、c_wrapper、tutorial） | 0 | 演示样例，非独立用例 |
| 基准 | 无 | 0 | 无基准目录 |
| fixture | tests/elf_examples/ 54 个 ELF 样本文件 | 0 | 测试数据，非用例 |
| 测试脚本 | tests/runELFtests、CMakeLists.txt、Makefile.am、configure.ac | 0 | 构建/运行脚本 |
| 构建目标 | ELFIOTest（单可执行，内嵌全部 36 用例）+ `check` 目标 | — | 单目标聚合 |

## 2. 独立上游用例清单（36 个）

### tests/ELFIOTest.cpp（13）
load32, load64, hello_64_o, hello_32_o, test_ppc_o, test_ppc,
test_dummy_out_i386_32, test_dummy_out_ppc_32, test_dummy_out_i386_64,
test_dummy_out_ppc_64, test_dynamic_64_1, test_dynamic_64_2, test_dynamic_64_3

### tests/ELFIOTest1.cpp（16）
write_obj_i386_32, write_obj_i386_64, write_exe_i386_32, elf_object_copy_32,
section_header_address_update, elfio_copy, elf_exe_copy_64, elf_exe_copy_32,
elf_exe_loadsave_ppc32big3, get_symbol_32, get_symbol_64, null_section_inside_segment,
invalid_file, rearrange_local_symbols, rearrange_local_symbols_with_reallocation,
detect_mismatched_section_segment_tables

### tests/ELFIOTest2.cpp（7）
modinfo_read, modinfo_write, array_read_32, array_read_64, init_array_read_64,
init_array_write_64, test_hex

## 3. 双口径统计

| 口径 | 数值 | 说明 |
|------|------|------|
| source_declared_total | **36** | 官方 tag 源码 tests/ 中 BOOST_AUTO_TEST_CASE 总数（13+16+7） |
| configured_executable_total | **36** | R04 以 boost/1.90.0 编译 ELFIOTest，36 用例全部实例化于单可执行 |
| executed_passed_total | **36** | R04 实际运行全部通过（run_rc=0） |
| failed | 0 | 0 失败 |
| 未运行/未实例化 | 0 | R04 无未运行项 |

**全量通过率: 36/36 (100.0%)**（R04，boost/1.90.0 实测）；
补充口径: executed/configured = 36/36 (100.0%)（当前配置可执行集合通过率）。
R03 及之前为 0/36 (0.0%)（boost/1.90.0.2.1 缺 Boost.Test 头，依赖阻塞，已按当时证据如实记录）。

## 4. 逐项映射（源码声明 → 条件 → 构建目标 → 注册项 → 执行日志）

| 阶段 | 内容 | 结果 |
|------|------|------|
| 源码声明/宏 | tests/ELFIOTest.cpp / ELFIOTest1.cpp / ELFIOTest2.cpp 共 36 个 BOOST_AUTO_TEST_CASE | 36 项声明 |
| 预处理/构建条件 | 官方 release tarball 不含 tests/ 目录（git tag 才有）；配方 `ELFIO_BUILD_TESTS=False`（generate() 显式关闭） | 构建条件不满足 |
| 构建目标 | tests/CMakeLists.txt 定义 `ELFIOTest`（需 find_package(Boost REQUIRED COMPONENTS unit_test_framework)）+ `check` 目标 | 目标不可构建 |
| ctest 注册项 | tests/CMakeLists.txt `add_test(NAME ELFIOTest ...)` | 未注册（目标未构建） |
| 实际执行日志 | 无（构建阻塞，无执行） | 无执行日志 |

## 5. 未运行原因（真实硬阻塞，逐项）

- **首条错误**: `fatal error: 'boost/test/included/unit_test.hpp' file not found`（ELFIOTest.cpp:28）；
  `'boost/test/unit_test.hpp' file not found`（ELFIOTest1.cpp:28 / ELFIOTest2.cpp:28）
- **命令**: `clang++ -std=c++17 -I<elfio-3.9.work> -I<upstream_tests> -I/usr/local/include ELFIOTest.cpp ELFIOTest1.cpp ELFIOTest2.cpp -o ELFIOTest`
- **cwd**: /storage/Users/currentUser/junshi_liu/worktrees/pc3-7-elfio-3.9/.elfio_audit_tmp
- **退出码**: 1（三文件均编译失败）
- **缺失条件**: Boost unit_test_framework 头文件——本机 `/usr/local/include` 无 boost；
  远端 registry `conan download boost/1.84.0 -r=ohpcd` 报 `Error downloading from remote 'ohpcd'`（连接失败）。
- **阻塞归属**: 依赖/基础设施阻塞（L0i 依赖可用性门禁），非当前库配方或源码错误。
  ELFIO 本身 header-only、无依赖；测试仅依赖 Boost 测试框架。官方 release 包亦不含 tests/。
- **恢复条件**: 提供 Boost（≥1.84 头文件）或恢复 registry 可达后，
  `cmake -DELFIO_BUILD_TESTS=ON` 构建 ELFIOTest 并运行 `./ELFIOTest`（runELFtests）。

## 6. 已实际运行并验证的本库验证项（非上游用例）

- test_package 消费者测试 `./test_elfio`：创建 ELF → 保存 → 读回 → 校验 class/encoding/machine/
  section/版本，**全部通过**（`All ELFIO API tests passed!`，退出码 0，详见 conan create 日志）。
- HarmonyOS 专项测试 `./test_harmonyos_elf`：解析真实 OHOS aarch64 ELF（/proc/self/exe）+
  aarch64 回写 round-trip，**PASSED**（退出码 0）。
- 两者均不属于上游独立用例（见 §1 分类）。

## 7. 结论

- 上游声明 36 个独立用例，当前配置 0 实例化、0 运行，通过率 0/36 (0.0%)；
  全部因 Boost 测试框架缺失硬阻塞，属外部依赖/基础设施问题，非 elfio 3.9 适配缺陷。
- release 包不含 tests/ 与配方 `ELFIO_BUILD_TESTS=False` 为真实约束（与已发布 3.12 一致）。
- 本台账为提交/运输版（docs/ 路径，随 PR 交付）；本地工作副本另见 reports/。
