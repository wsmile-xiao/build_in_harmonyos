# caches 0.1.1 适配笔记

## 概述

- 上游：https://github.com/vpetrigo/caches（BSD-3-Clause）
- 类型：C++11 header-only 缓存库（LRU/FIFO/LFU/NoPolicy 四种策略）
- 构建系统：CMake（INTERFACE target `caches`，可导出 `caches::caches`）
- 无运行时依赖；测试依赖 googletest（上游以子模块引入，官方 tar 不含子模块内容）

## 源码核验

- 官方 tag v0.1.1 tar.gz SHA-256：`ac822a2b3ff10f29e402dbbc3837fc0c7559e41b65157148e2caea1c4513e27b`
- 根 CMakeLists.txt：`project(caches VERSION 0.1.1)`；`CACHES_INSTALL_LIBRARY` 控制 install
- 头文件 5 个：`include/caches/{cache,cache_policy,fifo_cache_policy,lfu_cache_policy,lru_cache_policy}.hpp`（575 行）

## 上游测试台账（4 文件 / 35 个独立 TEST 用例，gtest）

| 文件 | TEST 数 | 实际运行 | 结果 |
|---|---|---|---|
| test/lru_cache_tests.cpp | 11 | 是（OHOS clang 15） | 11/11 通过 |
| test/fifo_cache_tests.cpp | 8 | 是 | 8/8 通过 |
| test/lfu_cache_tests.cpp | 8 | 是 | 8/8 通过 |
| test/nopolicy_cache_tests.cpp | 8 | 是 | 8/8 通过 |
| **合计** | **35** | ctest 4/4 | **35/35 (100%)** |

- `TEST_CASE` 字样仅出现在 TryGet 用例的局部常量名（`constexpr std::size_t TEST_CASE{10}`），非测试宏。
- 上游 CMakeLists 硬编码 `CMAKE_CXX_STANDARD 11`，但测试代码使用 C++17 特性
  （CTAD `std::array`、if 初始化语句），clang 15 默认 gnu++14 下会 `-Wc++17-extensions -Werror`。
  上游 CI 用现代 clang/gcc（默认 C++17）因此通过；OHOS 工具链需显式 `-std=c++17`。
  库本体头文件为纯 C++11，无需修改。
- deps/googletest 为 git 子模块，官方 tar 不含其内容（0 文件）；本地验证时以
  googletest release-1.12.1 源码填充构建。配方中 CACHES_BUILD_TEST=OFF，不把子模块
  缺失变成构建阻塞；上游测试已单独编译运行验证。

## HarmonyOS 适配要点

- 配方类型 header-library；`generate()` 设 `CACHES_INSTALL_LIBRARY=ON`（复用上游
  install 规则：include/ + caches::caches export + pkg-config）、`CACHES_BUILD_TEST=OFF`。
- test_package 两项消费者测试均在本机（aarch64 OHOS）真实运行通过：
  - `test_caches`（LRU/FIFO Put/Get/Size/Remove）
  - `test_caches_ohos`（四策略实例化、自定义类型、TryGet、std::thread 并发读写）
- 无补丁（patches/ 为空）；无二进制产物（header-only）。

## W3 本地 CI

- conan create 通过；test_package 两项测试 PASSED（见 reports/conan-create.log）。
- finish W3 写入 `.ci-result.json`（exit_code=0，log_sha256 见文件）。
- 说明：W3 JC full 模式曾命中 main 基线存量 `archives/u/util-linux-login/2.42.2/.ci-trigger`
  （其他 PR 合入的空文件），与本任务无关；分支提交后 JC 按 prdiff 模式仅扫描本 PR 文件，通过。

## 状态

- status: built（本地验证通过；制品发布由 CI release 流水线 upload）
- 知识候选：见知识候选台账（knowledge_candidate_ledger）——header-only 库适配
  无平台宏、无补丁、无链接问题，候选以"上游 CMakeLists C++11 硬编码与测试 C++17
  需求不一致"为唯一可复用观察。

## 知识候选台账与查重

- 候选 1（唯一非噪声候选）：上游 CMakeLists.txt `set(CMAKE_CXX_STANDARD 11)` 硬编码
  C++11，但测试代码使用 C++17 特性（CTAD `constexpr std::array access_order = {...}`、
  if 初始化语句 `if (const auto key = ...; cond)`）；OHOS clang 15 默认 gnu++14，
  测试目标带 `-Wall -Wextra -Wpedantic -Werror` → `-Wc++17-extensions` 硬错误。
  - 真实错误：`error: use of class template 'std::array' requires template arguments` /
    `error: 'if' initialization statements are a C++17 extension [-Werror,-Wc++17-extensions]`
  - 根因：上游声明标准低于测试代码实际需求；`set(CMAKE_CXX_STANDARD 11)` 为普通变量，
    会覆盖命令行 `-DCMAKE_CXX_STANDARD=17` 的 cache 变量，仅加 -D 无效
  - 修复：`-DCMAKE_CXX_FLAGS="-std=c++17"`（flags 在编译命令后段压过 -std=gnu++11）
    或改 set() 为 17；配方案例在 test_package 用 `CXX_STANDARD 17`
  - 验证：OHOS clang 15 构建 + ctest 4/4，35/35 TEST 全过（100%）
  - 适用范围：默认标准 <C++17 的工具链（OHOS clang 15、gcc<12）下，CMakeLists
    声明 C++11 但测试代码用 C++17 特性的 CMake 项目
  - 查重：
    - 正式知识（graph/doc）：E096（cmake-cxx-standard-explicit，根因=CMake 特性检测
      失败 System unknown to cmake）、E130（change-cxx-standard，根因=OHOS libc++
      头文件需 C++17）、E293（旧代码 C++17 移除特性）均只部分相关，未覆盖
      「CMakeLists set() 覆盖 -D cache 变量」机制与本签名 → 未命中/部分覆盖
    - 图谱 index.tsv：无同签名条目（E096/E130/E293 关键词相近但 error_signature 不同）
    - 草稿 drafts/：无相同签名草稿（C++17/standard/werror 相关草稿均不同库）
  - 七轴结论：exact_duplicate=否；causal_duplicate=否；trigger_overlap=部分（与 E096/E130
    同属 C++ 标准话题但触发签名不同）；solution_overlap=部分（都涉及显式设标准，但本
    候选的关键差异是 set() 覆盖 -D 的机制与 flags 后段压过）；combination_novelty=是
    （set() 覆盖机制 + 测试代码标准高于库声明）；boundary_novelty=是（适用边界=默认
    标准<17 工具链，反例=现代 clang 默认 C++17 不触发）；test_migration_novelty=否
  - 关系：`similar_to`=E096,E130,E293；`caused_by`/`prerequisite_of`/`conflicts_with`=无
- 路径决定：候选已验证、可跨库复用（任何 header-only/CMake 库测试用 C++17 而声明 C++11
  均适用）、查重为未命中且存在新增差异 → 走路径 B（知识库扩展），建立同 stem 草稿
  knowledge/drafts/E700-draft-57A5.kv/.md；决定 = `new_draft`。
---

**编译结束**: 2026-09-05 04:28
**最终状态**: built
