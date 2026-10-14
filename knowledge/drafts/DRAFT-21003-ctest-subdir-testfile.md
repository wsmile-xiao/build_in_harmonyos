# DRAFT-21003: CMake add_test 在子目录时 ctest --test-dir 必须指向子目录

- **来源**：lwjson 1.9.0 适配（2026-10-04，PR 待定）
- **相邻条目**：E292（layered-ctest-migration）、E294（dual-cmake-build-tree）

## 问题（一类）

CMake 工程的 `enable_testing()/add_test()` 写在子目录（如 `tests/CMakeLists.txt`），
顶层 `CMakeLists.txt` 只 `add_subdirectory(tests)`。此时 **CTestTestfile.cmake
只生成在 `<build>/tests/` 子目录**，顶层 `<build>/` 没有测试清单。在顶层构建目录
运行：

```
ctest --test-dir <build>
```

→ `No tests were found`（exit 0，静默通过）—— "测试没跑却以为通过"的假阳性。

配方的 `build()`/本地验证必须把 `--test-dir` 指向含 `add_test` 的子目录
（cmake_layout 下为 `<binary_folder>/tests`）。

## 验证（lwjson 1.9.0 实测）

- 顶层 `ctest --test-dir __build__` → "No tests were found"（顶层无
  CTestTestfile.cmake）；
- `ctest --test-dir __build__/tests --output-on-failure` → `1/1 Test #1: Test Passed`；
- conan create build() 内同上（`<build>/Release/tests`）→ 1/1 Passed；
  上游 6 个独立测试入口逐一 `-DTEST_CMAKE_FILE_NAME=.../cmake.cmake` 配置构建后，
  各自 ctest 于子目录全部 6/6 Passed。

## 适用边界

- 只适用于 add_test 位于子目录的工程；顶层 add_test（如常见 test_package
  模板）无此问题。
- 反例：`enable_testing()` 在顶层 CMakeLists 时顶层 CTestTestfile.cmake 正常生成，
  无此陷阱。
- "No tests were found"≠"上游无测试"，须先定位 CTestTestfile.cmake 位置再下结论
  （R51 台账口径：不得把未正确定位的入口记为未运行/无测试）。

## 与既有知识的关系（七轴查重）

| 轴 | 结论 |
|----|------|
| exact_duplicate | 否 |
| causal_duplicate | 否（E292/E294 聚焦 CTest 分层迁移与双构建树，根因不同） |
| trigger_overlap | 无 |
| solution_overlap | 无 |
| combination_novelty | 有：子目录测试清单定位 + build() 内真实计数断言 |
| boundary_novelty | 有：顶层/子目录 add_test 判别 + 假阳性识别 |
| test_migration_novelty | 有:与 R51 台账衔接（"No tests were found"需先定位清单） |

**决策**：new_draft（DRAFT-21003）。