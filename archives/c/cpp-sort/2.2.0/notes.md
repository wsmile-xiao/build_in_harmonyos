# cpp-sort 2.2.0 适配笔记（pc3-21）

## 来源核验（source_audit）
- 官方仓库：https://github.com/Morwenn/cpp-sort
- 正式标签：`v2.2.0`（GitHub archive `refs/tags/v2.2.0`）
- 源码 tarball：`https://github.com/Morwenn/cpp-sort/archive/refs/tags/v2.2.0.tar.gz`
- SHA-256：`c097a17c895fa684b92f6af45e8464e7179f0d73145826942add09daa5ca0c22`（tarball 实测，与 tarball 内 `.tarball-sha256` 一致）
- CMakeLists.txt 确认 `project(cpp-sort VERSION 2.2.0 LANGUAGES CXX)`
- 许可证：MIT（LICENSE.txt）

## 结构
- header-only C++17 库（CMake INTERFACE library），无任何第三方运行时依赖
- 目录：`include/cpp-sort/`（sorters/、adapters/、comparators/、metrics/、probes/、utility/、fixed/ 等）
- 上游自带 conanfile.py（`package_type = "header-library"`）与本仓库 CMake 安装规则
- 测试：Catch2 v3.15.3 + RapidCheck（FetchContent 引入），`tests/CMakeLists.txt` 定义
  `main-tests` 与 `heap-memory-exhaustion-tests` 两个可执行

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-02
- 编译器: clang 15.0.4（/data/service/hnp/bin/clang++）
- 交叉目标: aarch64-linux-ohos（Conan profile: ci/conan/profiles/ohos-aarch64）
- 状态: built

## 编译步骤
1. `conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64`
   → 通过（header-only 打包 include/ + CMake config，test_package 1/1 通过）
2. 上游测试全量构建运行：
   `cmake -S . -B build-tests -DBUILD_TESTING=ON -DCPPSORT_BUILD_TESTING=ON
     -DFETCHCONTENT_SOURCE_DIR_CATCH2=… -DFETCHCONTENT_SOURCE_DIR_RAPIDCHECK=…
     -DFETCHCONTENT_FULLY_DISCONNECTED=ON`
   `make -j2` → `ctest --output-on-failure -j2` → **1462/1462 通过（100%）**
3. OHOS 专项测试：`clang++ -std=c++17 -O2 ohos_special_test.cpp` → PASSED
   （hybrid_adapter 大规模随机排序 + merge_sort 稳定性 + sorting_network_sorter<8>）

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `cpp-sort/sort.h` 不存在 | cpp-sort 2.x 无泛型 `<cpp-sort/sort.h>`，统一入口为 `sorters.h` 提供的各 sorter_facade 常量 | test_package/test.cpp 改用 `cppsort::merge_sort`、`cppsort::adaptive_shivers_sort`（已验证） |
| 2 | `cppsort::utility::make_buffer` / `projection_compare` 不存在 | 2.x 移除该工具；固定大小排序走 `cpp-sort/fixed_sorters.h` 的 `sorting_network_sorter<N>` | test_package/test.cpp 与 ohos_special_test.cpp 按 2.x API 修正（已验证） |

## 验证结果
- 上游测试全量：1462/1462 = 100%（详见 reports/upstream-test-ledger.md）
- OHOS 专项测试：PASSED（logs/ohos-special-test.log）
- conan-verify 8 门禁 G0-G4/L2/L4/L5：PASS（reports/conan-verify-report.md）
- W3 本地 CI 模拟：PASS（reports/w3-local-ci.log，.ci-result.json exit_code=0）
- test_package 消费者验证：test_cpp-sort 1/1 通过（conan create 内执行）

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | header-only CMake recipe（package_type=header-library） |
| conandata.yml | 官方 v2.2.0 tarball + SHA-256 |
| test_package/ | 消费者测试（merge_sort/adaptive_shivers_sort） |
| ohos_special_test.cpp | HarmonyOS 专项测试 |
| reports/upstream-test-ledger.md | 上游 1462 用例完整台账 |

## 注意事项
- cpp-sort 2.x 的 API 与 1.x 差异较大（无 sort.h/make_buffer），下游消费须以 sorters.h 为入口
- 无第三方依赖，L0i 依赖可用性检查不涉及当前库之外的对象
---

**编译结束**: 2026-09-03 02:20
**最终状态**: built
