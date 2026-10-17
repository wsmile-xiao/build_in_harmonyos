# DRAFT-cpplocate-2.3.0-test-package-reliability

> 草稿知识项 — test_package 的 HarmonyOS 专项测试可信度整改模式
> 来源：cpplocate 2.3.0 PR #7616 R02 审查整改（pc1-83，2026-09-02）
> 同 stem 配对：`knowledge/drafts/DRAFT-cpplocate-2.3.0-test-package-reliability.kv`

## 问题（现象 / error_signature）

- 专项测试只用 `assert()` 判定成败；Conan `build_type=Release` 注入 `-DNDEBUG` 后 `assert` 整体不求值，测试在任何失败场景下都返回 0（静默通过），`ALL_*_ASSERTIONS_PASSED` 成为空话。
- `locatePath` 等路径解析 API 没有建立真实文件前置条件时，只能打印空结果（空转），无法证明"相对路径可解析"。
- 专项测试未放入 `test_package/CMakeLists.txt` 的 `add_test`，仅手动单独运行，不进入 `conan create` 的自动化路径，CI 无法证明其被执行。
- 测试头注释里的链接命令（如 `-lloc`）与 recipe 实际链接目标不一致，误导维护者复现。

## 根因（root_cause）

1. `-DNDEBUG` 下 `assert(expr)` 展开为 `((void)0)`，测试若以 assert 作为唯一判定手段则损失全部失败路径。
2. `locatePath` 基于 exe/lib 目录及父级逐层查找 `relpath`；不先创建文件则必然返回空，检查退化为打印。
3. `test_package/conanfile.py::test()` 只 `cmake.test()`，未在 CMakeLists 注册的测试不会被执行到。
4. 注释命令未与 `conanfile.py::package_info().cpp_info.libs` 对照。

## 可复用方案（rec_approach: check-macro-and-resource-precondition-and-ctest）

1. **CHECK 宏替代 assert（NDEBUG 安全）**：
   ```cpp
   #define CHECK(cond) do { if (!(cond)) { std::printf("FAIL: %s (line %d)\n", #cond, __LINE__); return 1; } } while (0)
   ```
2. **locatePath 建立可验证前置条件**：在模块目录创建真实数据文件，断言 `locatePath` 返回非空且 `fileExists(返回路径)` 为真，失败返回非零。
3. **纳入 test_package 自动化门禁**：
   ```cmake
   add_executable(test_<lib>_hmos test_<lib>_hmos.cpp)
   target_link_libraries(test_<lib>_hmos <pkg>::<lib>)
   add_test(NAME test_<lib>_hmos COMMAND test_<lib>_hmos)
   ```
4. **注释/文档链接命令与实际 recipe 一致**：以 `package_info().cpp_info.libs` 为准核对 `-l` 目标。

## 适用条件

- 在 test_package 中投放平台专项（OHOS 等）验证测试的库配方；
- Release/NDEBUG 生效的构建路径；
- 含路径解析类 API（locatePath/getModulePath 等）或需要"前置条件 → 断言"的库。

## 反例（不适用场景）

- 上游已有 gtest/gmock 完整断言机（`ASSERT_*` 宏本身含失败路径）的常规测试，不需要 CHECK 宏；
- 无需平台专项验证的纯计算库。

## 验证证据（真实命令 + 结果）

- 整改后 `test_cpplocate_hmos.cpp`：CHECK 宏 + 前置条件 + NDEBUG 安全；
- 双构建双运行：常规与 `-DNDEBUG` 均编译 exit 0、运行 `ALL_CPPLOCATE_HMOS_ASSERTIONS_PASSED` exit 0；
- test_package 自动化：`conan create` 日志 `Test #2: test_cpplocate_hmos ... Passed`，`100% tests passed, 0 tests failed out of 2`；
- W3 本地 CI：`L0_RESULT=pass`，Pass rate 100%（1/1）；
- `-lloc` 已修正为 `-llocate`（全目录 grep 无残留）。

## 限制与恢复条件

- CHECK 宏约定在测试源文件内定义，需保持不变式（打印 + 非零退出）；
- 若上游测试已纳入 test_package 自动化（`add_test` 已存在），仅需迁移断言方式；
- 恢复条件：删除 CHECK 宏改用标准断言器时，必须确认目标框架在 NDEBUG 下保留失败路径，否则回到静默通过问题。