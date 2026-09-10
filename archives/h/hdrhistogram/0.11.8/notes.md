# HdrHistogram_c 0.11.8 适配笔记

## 编译环境
- 构建系统: cmake (4.1.2)
- 编译日期: 2026-09-06
- 编译器: clang 15.0.4 (OHOS SDK 26.0.0.18)
- 目标平台: HarmonyOS PC (aarch64, os=OHOS)
- 状态: built

## 编译步骤
1. 源码下载：官方 GitHub tag `0.11.8`（`https://github.com/HdrHistogram/HdrHistogram_c/archive/refs/tags/0.11.8.tar.gz`），SHA-256 `bb95351a6a8b242dc9be1f28562761a84d4cf0a874ffc90a9b630770a6468e94`
2. CMake 配置：`cmake .. -DHDR_LOG_REQUIRED=ON -DHDR_HISTOGRAM_BUILD_PROGRAMS=ON -DBUILD_TESTING=ON`（zlib 由配方从 OHOS sysroot 注入，见 conanfile.py generate()）
3. 编译：`make -j4`
4. 测试：`ctest`（5 个测试可执行文件，64 例全部通过）

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | clock_gettime 和 CLOCK_MONOTONIC 未定义 | OpenHarmony time.h 未定义这些常量 | 补丁添加 time.h/unistd.h 头文件和条件宏定义 |
| 2 | GitHub 无法直接访问 | 网络限制 | 使用镜像 URL 下载源码（conandata 保持官方 HTTPS URL） |
| 3 | hdr_histogram_log_test 未实例化 | 上游 `if(HDR_LOG_ENABLED)` 依赖 zlib；conan 工具链不搜 sysroot | 配方 generate() 从 OHOS sysroot 注入 ZLIB_INCLUDE_DIR/ZLIB_LIBRARY，恢复 log 组件与 25 例 log_test |
| 4 | hdr_histogram_atomic_concurrency_test 未实例化 | 上游 `if(UNIX)` 在 OHOS 不成立 | 补丁 0003 增加 OHOS/HarmonyOS 平台判定，恢复并发测试 1 例 |

## 源码修改（补丁）
| 文件 | 修改内容 | 补丁 |
|------|----------|------|
| src/hdr_time.c | 添加 time.h/unistd.h 头文件，定义 CLOCK_MONOTONIC/CLOCK_REALTIME 宏 | 0001-src-hdr_time.c.patch |
| test/hdr_histogram_perf.c | 添加 --version/--help 快速返回，避免性能基准在命令探测中长跑 | 0002-test-hdr_histogram_perf.c.patch |
| test/CMakeLists.txt | `if(UNIX)` → 增加 OHOS/HarmonyOS，启用 hdr_histogram_atomic_concurrency_test | 0003-test-CMakeLists.txt.patch |

## 依赖版本
- pthread (libpthread)
- rt (librt - clock_gettime)
- m (libm)
- zlib 1.3.1（OHOS sysroot 系统库，`/data/service/hnp/ohos-sdk.org/*/ohos/native/sysroot`，用于 HDR_LOG 组件）

## 上游测试枚举台账（双口径）

### 口径一：源码声明总数（source_declared_total = 64）
按官方 tag 0.11.8 源码中 `mu_run_test()` 可复制枚举规则统计的用户独立测试用例：

| 测试源文件 | 独立用例数（mu_run_test） | 备注 |
|------------|---------------------------|------|
| test/hdr_histogram_test.c | 18 | 主测试，minunit 框架 |
| test/hdr_histogram_atomic_test.c | 16 | 原子操作测试 |
| test/hdr_atomic_test.c | 4 | 原子 API 测试 |
| test/hdr_histogram_atomic_concurrency_test.c | 1 | 并发记录测试（上游 `if(UNIX)` 守卫，本轮补丁 0003 纳入 OHOS） |
| test/hdr_histogram_log_test.c | 25 | 日志组件测试（上游依赖 zlib，本轮配方注入 sysroot zlib 后纳入） |
| **合计** | **64** | |

### 口径二：当前 OHOS 配置实际实例化（configured_executable_total = 64）
CMake 注册的可执行测试目标（ctest -N）：

| 构建目标 | 注册用例数 | 实例化条件 | 实际执行 |
|----------|-----------|------------|----------|
| hdr_histogram_test | 18 | 无条件 | ✅ 运行，ALL TESTS PASSED，exit 0 |
| hdr_histogram_atomic_test | 16 | 无条件 | ✅ 运行，ALL TESTS PASSED，exit 0 |
| hdr_atomic_test | 4 | 无条件 | ✅ 运行，ALL TESTS PASSED，exit 0 |
| hdr_histogram_log_test | 25 | zlib 可用（本轮注入 sysroot zlib） | ✅ 运行，ALL TESTS PASSED，exit 0 |
| hdr_histogram_atomic_concurrency_test | 1 | UNIX/OHOS/HarmonyOS（本轮补丁 0003） | ✅ 运行，ALL TESTS PASSED，exit 0 |

### 执行结果
- **executed_passed_total = 64 / source_declared_total = 64（100.0%）**
- 失败 0、未运行/未实例化 0
- ctest 汇总：`100% tests passed, 0 tests failed out of 5`（全量通过率以源码声明 64 为分母：64/64 = 100%）
- 逐项映射：源码 mu_run_test 声明 → test/CMakeLists.txt 注册目标（add_test）→ ctest 运行 → 可执行文件 "ALL TESTS PASSED / Tests run: N" 输出（exit 0）

### 台账其余条目（非独立用例，不计入上游用例数）
| 条目 | 分类 | 说明 |
|------|------|------|
| test/minunit.c / minunit.h | 测试框架 | minunit 框架实现，非用户用例 |
| test/hdr_test_util.h | 测试工具头 | 断言辅助，非用户用例 |
| test/hdr_histogram_perf.c | 基准/性能工具 | 性能基准（add_test_executable，未注册为 ctest 测试） |
| test/hdr_histogram_benchmark.cpp | 基准 | google_benchmark 微基准，需 `HDR_HISTOGRAM_BUILD_BENCHMARK=ON`，默认 OFF 不构建 |
| test/vendor/google/benchmark-1.6.1.zip | 基准依赖 | google_benchmark 源码包，仅基准启用时使用 |
| test/jHiccup-*.hlog（4 个） | fixture | 日志测试输入数据 |
| test/test_tagged_*.txt（4 个） | fixture | 标签化日志测试输入数据 |
| examples/hdr_decoder.c、examples/hiccup.c | 样例 | 示例程序，非测试用例 |
| lib/benchmark-1.6.1.zip | 基准依赖 | google_benchmark 打包文件 |

## 验证结果
- 上游测试：64/64（100%）全部通过（5 个测试可执行文件）
- conan create（OHOS profile）：构建成功，SONAME 设置 + 重签完成，test_package 消费者测试通过
- 双口径一致：源码声明 64 = 当前配置可执行 64 = 实际执行通过 64

## 交付物
| 文件 | 说明 |
|------|------|
| libhdr_histogram.so | 动态共享库（含 SONAME） |
| libhdr_histogram_static.a | 静态库 |
| bin/hdr_histogram_test 等 5 个测试可执行 | 测试程序（安装到 bin/） |

## 知识候选台账与查重（七轴）

### 候选清单
| # | 候选 | 触发错误/现象 | 根因 | 修复 | 验证 | 适用范围 |
|---|------|--------------|------|------|------|----------|
| C1 | OHOS 缺 CLOCK_MONOTONIC/CLOCK_REALTIME | `use of undeclared identifier 'CLOCK_MONOTONIC'`（hdr_time.c） | OHOS sysroot time.h 未定义 POSIX 时钟常量 | 源补丁 include time.h/unistd.h + `#ifndef` 定义常量 | conan create 构建通过，时间 API 专项测试通过 | 任何在 OHOS 直接调用 clock_gettime(CLOCK_*) 的 C 库 |
| C2 | 上游 `if(UNIX)` 守卫不识别 OHOS | ctest 未注册 hdr_histogram_atomic_concurrency_test | CMake 在 OHOS 下 CMAKE_SYSTEM_NAME=HarmonyOS，非 UNIX | 补丁扩展守卫为 `if(UNIX OR OHOS OR HarmonyOS)` | 并发测试 1/1 通过 | 任何用 `if(UNIX)` 门控测试/目标的 CMake 项目 |
| C3 | conan 工具链 find_package(ZLIB) 失败，log_test 未实例化 | `Could NOT find ZLIB (missing: ZLIB_LIBRARY ZLIB_INCLUDE_DIR)` | conan CMakeToolchain 默认不搜 OHOS sysroot | 配方 generate() 注入 sysroot 的 ZLIB_INCLUDE_DIR/ZLIB_LIBRARY | log_test 25/25 通过，64/64 全量通过 | 依赖 sysroot 系统库（zlib 等）但用 find_package 的 OHOS 配方 |

### 四范围查重结果
| 候选 | 正式知识 (index.tsv/doc) | 图谱 (graph/) | 草稿 (drafts/) | 归档 (archives/) |
|------|--------------------------|---------------|----------------|------------------|
| C1 | E138（disable-posix-timer）、E152（add-cflags）同错误签名 | 命中 E138/E152 | 无独立草稿 | 0.11.9/0.11.9.1 同补丁已归档 |
| C2 | E532（harmonyos-into-unix-branch）、E140/E267（add-harmonyos-cmake-detection）覆盖平台守卫模式 | 命中 E532 | 无 | 29 个配方有 ZLIB 注入，但均为依赖包注入 |
| C3 | 未命中 find_package 系统库注入条目（E323/E438 为依赖包 CMAKE_PREFIX_PATH，非 sysroot 系统库） | 未命中 | kpackage 草稿为消费者侧 find_dependency，非生产者侧 sysroot 注入 | assimp/aevol 用依赖包路径，非 sysroot |

### 七轴查重
| 轴 | C1 | C2 | C3 |
|----|----|----|----|
| exact_duplicate | 否（E138/E152 方案不同：disable/add-cflags vs 源定义） | 否（E532 针对三分支，此为单守卫测试注册） | 否 |
| causal_duplicate | 是（根因同为 OHOS 缺 POSIX 常量） | 部分（同为 CMAKE_SYSTEM_NAME 不识别） | 否 |
| trigger_overlap | 是（错误签名一致） | 是（UNIX 判定不一致） | 部分（"Could NOT find ZLIB" 签名与 kpackage 相同，但场景不同） |
| solution_overlap | 部分（源定义 vs cflags） | 是（同为扩展平台判定） | 否（sysroot 注入 vs 依赖包注入/消费者 CMakeDeps） |
| combination_novelty | 低 | 中 | **高**：sysroot 系统库注入恢复 find_package 门控的上游测试入口，配合双口径台账 |
| boundary_novelty | 低 | 中 | **高**：明确了 OHOS 下"配方注入 sysroot 库路径 → find_package 命中 → 测试入口从 uninstantiated 恢复"的完整链路 |
| test_migration_novelty | 低 | 中 | **高**：log_test 25 例从不可实例化恢复到实际运行通过，双口径台账 64/64 一致 |

### 关系字段
- C1: similar_to=[E138, E152], caused_by=OHOS libc 头文件差异
- C2: similar_to=[E532, E140, E267], prerequisite_of=C3（测试入口可恢复的前提）
- C3: similar_to=[E323, E438, DRAFT-kpackage-karchive-619], conflicts_with=依赖包注入方式（本方案无需 conan 依赖，直接用 sysroot 系统库）

### 适用边界 / 反例
- C3 仅适用于"库确实消费 sysroot 系统库"的场景；若库应依赖 conan zlib 包（需版本锁定），应改用 self.requires + 依赖包注入（assimp 模式），不得混用。
- C2 仅扩展判定不改变行为：并发测试在 OHOS pthread 可用时才纳入；无 pthread 的平台仍不注册。

### 路径决定
- C1：**reuse_existing**（复用 E138/E152 知识，方案差异不足以建新条目）
- C2：**reuse_existing**（E532 已覆盖平台守卫模式）
- C3：**new_draft**（sysroot 系统库注入恢复 find_package 门控测试入口 + 双口径台账，未命中既有条目、已验证 64/64、可跨库复用）
- 总体：**路径 B（知识库扩展）**，建立草稿 DRAFT-hdrhistogram-c-0.11.8-sysroot-lib-inject-test-recovery（.kv/.md 同 stem）
---

**编译结束**: 2026-09-07 01:47
**最终状态**: built
