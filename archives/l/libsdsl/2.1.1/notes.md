# libsdsl 2.1.1 适配笔记

> 分支： feat/libsdsl-2.1.1
> 路径： 路径 A（基础适配）
> 最后更新： 2026-09-17

## 一、基本信息

| 项目 | 值 |
|------|-----|
| 软件 | libsdsl |
| 版本 | 2.1.1 |
| 状态 | built（真机预检通过，CI 校验通过） |
| 构建系统 | cmake |
| 源码 URL | https://github.com/simongog/sdsl-lite/archive/refs/tags/v2.1.1.tar.gz |
| 源码 sha256 | e36591338c390184760dbdddbb653d972d9c1986c8819f462e7e73ddd28b992b |
| 随源码 vendor | libdivsufsort 2.0.1（sha256 见 conandata.yml）、googletest 1.14.0（sha256 见 conandata.yml） |
| 许可 | GPL-3.0-or-later |
| 产物 | libsdsl + libdivsufsort + libdivsufsort64，头文件位于 include/sdsl |
| 上游仓库 | https://github.com/simongog/sdsl-lite |

## 二、编译环境与步骤

- 编译器： clang / clang++（OHOS SDK，Conan tools.build:compiler_executables 指向为空时按 PATH/SDK 回退探测）。
- 配置要点（conanfile.py `generate()`）：
  - `CMAKE_POLICY_VERSION_MINIMUM=3.5`（上游声明 cmake_minimum_required 2.8，与 CMake 4.x 兼容）。
  - OHOS 下 `CMAKE_SYSTEM_NAME=Linux`、`CMAKE_SYSTEM_PROCESSOR=aarch64`（CMake 无 HarmonyOS 平台模块，按 Linux-kernel 目标处理）。
  - `CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY`（编译器探测只编译不链接）。
  - 可写 TMPDIR 注入 `conanbuild.sh`（hmbs_tmpdir 脚本），避免只读 /tmp 导致编译器探测失败。
  - dangling 的 conf 编译器路径回退：补丁生成的 `conan_toolchain.cmake` 中的坏路径并导出 CC/CXX。
- 构建（`build()`）：`cmake.configure()` + `cmake.build()` + `cmake.install()`，`BUILD_SHARED_LIBS` 跟随 `shared` 选项（默认 OFF），`CODE_COVERAGE=OFF`、`GENERATE_DOC=OFF`。

## 三、遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 官方 release tarball 中 `external/` 子模块为空目录 | GitHub archive 不含 submodule 内容 | `source()` 中分别下载 libdivsufsort 2.0.1 与 googletest 1.14.0 并解到 `external/libdivsufsort`、`external/googletest`（路径与 `external/CMakeLists.txt` 期望一致） |
| 2 | CMake 4.x 直接报错（上游 `cmake_minimum_required(VERSION 2.8)`） | 旧声明与新 CMake 策略检查不兼容 | cache 变量 `CMAKE_POLICY_VERSION_MINIMUM=3.5`（须为 cache 变量才能在早期策略检查生效） |
| 3 | `project()` 报 System unknown / 编译器识别 unknown | `CMAKE_SYSTEM_NAME=HarmonyOS` 无对应平台模块；profile 的编译器路径在部分 worker 上不存在 | OHOS 时强制 `CMAKE_SYSTEM_NAME=Linux`；`_override_broken_conf_compiler` 按 isfile 探测并回退 PATH/SDK 中的 clang，同时补丁已生成的 toolchain 文件与 CC/CXX |
| 4 | `inv_perm_support_test` 二进制缺失 | `test/inv_perm_support_test.cpp` 使用 C++17 已移除的 `std::random_shuffle`，新标准下为硬构建错误 | 改写为带具名 `mt19937_64` 引擎的 `std::shuffle`（循环前单引擎，语义仍为随机置换；C++11 兼容） |
| 5 | aarch64 下位运算回退路径不可靠 | 上游 `bits.hpp` 仅在 `__SSE4_2__` 下使用 `__builtin_popcountll/clzll/ctzll`，aarch64 走通用表路径 | 四处守卫扩展为 `#if defined(__SSE4_2__) \|\| defined(__aarch64__)`；顶部的 `<xmmintrin.h>` 保持仅 x86；x86 行为不变 |
| 6 | `int_vector_mapper_test.temp_buffer_test` 报 could not create temporary file | 无参 `temp_file_buffer::create()` 硬编码 `tmp_file("/tmp")`，而真机 /tmp 只读 | `int_vector_mapper.hpp` 中按 `TMPDIR` / `TMP` / `TEMP` / `HMBS_TMPDIR` 顺序逐个 getenv 尝试，最后回退 `/tmp`（顺序判空，不用以空指针为终止条件的指针数组循环）；断言与 delete 语义不变 |
| 7 | 7 个 file-backed 套件直接运行报 `Usage: <exe> tmp_dir` 并 exit(1) | 这些套件的 `main()` 要求 `argv[1]` 为可写暂存目录 | 每个套件分配独立子目录（`upstream_tmp/<suite>`，运行前清理顶层遗留 regular 文件），按 `_TESTS_NEED_TMPDIR` 集合传参；bits/coder/sd_vector 无需参数 |

## 四、上游测试套件审计

- 审计对象：官方 v2.1.1 源码包（SHA-256 已校验），`test/` 目录 + `test/CMakeLists.txt`，gtest 随源码 vendor。
- 总量：上游共 24 个 gtest 程序，约 162 个 `TEST` / `TEST_F`。
- 离线可跑（10 个，已全部接入并在 `build()` 中真实执行）：bits、coder、int_vector、int_vector_buffer、int_vector_mapper、inv_perm_support、nn_dict_dynamic、sd_vector、sorted_int_stack、sorted_stack_support。
- 在线重型（14 个，未运行）：需要下载 Pizza&Chili 语料（faust / zarathustra / moby 等），单套最长可达 60 分钟，受限环境无法获取，已在 PR 正文补充说明中如实声明。
- 真机实测（离线子集）：67 / 67 通过（`HMBS_UPSTREAM_TEST_RESULT`，framework=gtest，failed=0，skipped=0）。
- 防假阳性：harness 解析每个二进制的 `Running N tests` / `PASSED` / `FAILED` 计数；0 用例计为失败；非零退出但失败数为 0 也计为失败；失败套件输出 `HMBS_UPSTREAM_FAIL_DETAIL` 并做诊断性重试（重试只记录日志，不改变计数）。

## 五、源码修改

- `conandata.yml` patches：无（`patches_applied: []`）。以下三处为 `source()` 阶段的源码级可移植修复（语义不变）：
  1. `test/inv_perm_support_test.cpp`：`random_shuffle` → `shuffle`（见上表 #4）。
  2. `include/sdsl/bits.hpp`：aarch64 启用 builtin cnt/sel/hi/lo（见上表 #5）。
  3. `include/sdsl/int_vector_mapper.hpp`：临时文件目录尊重可写 TMPDIR 链（见上表 #6）。
- 其余构建链适配（平台选择、编译器回退、TMPDIR 注入、SDK llvm/lib 的 `LD_LIBRARY_PATH` 补充）均在配方 `generate()` / `build()` 内完成，不修改上游源码。

## 六、test_package（消费者视角）

- `test_package/test_sdsl.cpp`：6 个 CHECK（bit_vector 存取、rank_support_v 两次 rank、select_support_mcl、三次 select、int_vector 回环与宽度、sd_vector 视图 size+popcount），任一失败即 exit(1)。
- 运行：`ctest --output-on-failure -R test_sdsl`，真机实测 6 / 6 通过（`HMBS_TEST_PACKAGE_RESULT`）。
- `test_package/MANIFEST.yml`：`upstream_tests_exist: true`，含 10 个离线套件清单与消费者用例声明（`assertion_count: 6`）。

## 七、验证记录

- 真机预检：编译通过；上游离线 67 / 67；test_package 6 / 6。
- CI：PR #9969 构建 #47043 校验通过（Conan test_package、L0 结构完整性、L1 测试执行验证；各步骤 worker_preparation → cleanup 均为 ✅）。此前的 #47014 / #47041 在 git-clone/cleanup 步骤失败，为 Worker 基础设施类失败，与配方无关，重试后通过。
- AI 审查：无 P0/P1（未发现问题）。

## 八、注意事项

- 本适配为路径 A（基础适配），产物与上游 ABI/行为保持一致，不形成新的跨库知识。
- 14 个重型在线套件未在设备/CI 内运行；如需全量验证，需先解决 Pizza&Chili 语料的离线供给问题。
- `archives/l/libsdsl/README.md` 与 `manifest.yaml` 记录了 OHOS 适配要点与版本状态；本文件为版本级构建笔记。
