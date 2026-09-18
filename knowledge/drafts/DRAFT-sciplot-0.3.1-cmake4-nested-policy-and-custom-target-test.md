# DRAFT: CMake4 嵌套测试子项目 policy 下限 + 自定义测试 target（sciplot 0.3.1 实证）

> 配套 `.kv`: `DRAFT-sciplot-0.3.1-cmake4-nested-policy-and-custom-target-test.kv`
> 来源库: sciplot 0.3.1（header-only C++17 绘图库）| 2026-09-16 | conan-verify G2 实证

## 问题

sciplot 0.3.1 在 OHOS CMake 4.1.2 工具链下 `conan create` 出现两类 G2 失败：

1. **configure 阶段**: 嵌套测试子项目 `tests/testing-project/CMakeLists.txt` 声明
   `cmake_minimum_required(VERSION 3.0)`，CMake 4.x 直接拒绝：
   ```
   CMake Error at tests/testing-project/CMakeLists.txt:1 (cmake_minimum_required):
     Compatibility with CMake < 3.5 has been removed from CMake.
   ```
2. **build 阶段**: 上游 `tests/CMakeLists.txt` 用 `add_custom_target(tests ...)`
   注册测试而非 CTest 的 `enable_testing()/add_test()`，`cmake.test()` 固定构建
   `test` 目标时失败：
   ```
   make: *** No rule to make target 'test'.  Stop.
   ConanException: Error 2 while executing
   ```

## 根因

1. CMake 4.x 移除了对 `<3.5` 的兼容策略。此前的 E321/E103/E187 记录的场景是主项目
   顶层 `cmake_minimum_required(<3.5)`；sciplot 证明**主项目满足 >=3.5、仅嵌套
   add_subdirectory 的子项目声明 <3.5 时同样被拒**。
2. Conan 2 的 `cmake.test()` 固定构建 CTest 约定的 `test` 目标；对以自定义 target
   （`add_custom_target`）注册上游测试的项目，目标不存在，测试无法经 `cmake.test()` 跑通。

## 方案

1. **policy 下限（子项目场景）**: 配方 `generate()` 用 `CMakeToolchain` 的
   `tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"`。与 E321 主张（主项目顶层
   场景必须 `cache_variables`，因 toolchain 文件加载晚于主项目首行 `cmake_minimum_required`）
   不同，**嵌套子项目场景下 `tc.variables` 有效**：toolchain 在主项目 CMakeLists 解析时
   加载，嵌套子目录的 `cmake_minimum_required` 在 `add_subdirectory` 时才处理，此时变量
   已生效。sciplot 实测 `tc.variables` 即通过 G2，无需 `cache_variables`。
2. **自定义测试 target**: 配方 `build()` 不调 `cmake.test()`，直接运行测试二进制：
   ```python
   tests_bin = os.path.join(self.cpp.build.bindirs[0], "tests", "sciplot-cpptests")
   self.run(tests_bin, env="conanrun")
   ```

## 验证

- `conan-verify sciplot 0.3.1` 全部门禁 PASS（G1-G4, L2/L4/L5），上游 24 个
  TEST_CASE / 180 assertions 全过：
  ```
  All tests passed (180 assertions in 24 test cases)
  ```
- 日志: `archives/s/sciplot/0.3.1/reports/conan-create.log`、`conan-verify-report.md`
- SHA-256（源码）: `d5f8fa7783920c0db4f54d8d9cea8a5e50be99153e81dcaccf91532994ebbad0`

## 适用边界

- 仅适用于**嵌套子项目**声明 `<3.5` 的场景（主项目顶层场景仍按 E321 用 cache_variables）
- 上游测试为自定义 target 而非 CTest 注册时适用"直接运行测试二进制"
- 不适用: 上游 CTest 注册正常的项目（应继续用 `cmake.test()`）

## 反例 / 边界

- 若主项目顶层 `cmake_minimum_required(<3.5)`（E321 场景），`tc.variables` 无效，
  必须 `cache_variables`，两者不可互换
- header-only 库 `self.cpp.build.bindirs[0]` 可能不含测试二进制目录，需按实际
  CMake 输出目录拼接（sciplot 为 `tests/` 子目录）

## 关系

- `similar_to`: E321（cmake4 policy minimum）、E187（add-cmake-flag）、E103（bump-cmake-minimum-version）
- `caused_by`: cmake4-policy-removal
- `conflicts_with`: 无
