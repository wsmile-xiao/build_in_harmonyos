# E321 — GTest 伪随机输入跨标准库差异 + CMake 项目测试目标未 add_test 注册的层1集成陷阱

## 错误特征
两类可独立出现的症状：
- 症状 A（伪随机输入跨标准库）：同一 GTest 用例在 libstdc++(GCC/Clang, Linux) 下通过，但在 OHOS(libc++) 下失败，断言的是某段由 `std::uniform_int_distribution` 生成的伪随机字节的硬编码期望值。
- 症状 B（CMake 项目测试未注册 → ctest 静默 0 测试）：`enable_testing()` 已调用、测试目标也能编译链接，但 `ctest` 报 0 个测试并通过；或 CI 侧 `grep ctest/make check` 认为"跑了上游测试"实际一个没跑。

## 触发条件
- 构建系统: **症状 A 任意 C/C++ 项目（含 GTest/gmock）；症状 B 仅限 CMake（CTest）项目**
- 阶段: 测试执行 / 测试发现
- 关键点（症状 B）：上游调用了 `enable_testing()` 但核心测试目标只用 `add_executable` 构建、**从未 `add_test()` 注册**（barrier 的 unittests/integtests 即如此——全仓库唯一 add_test 是 GUI 测试 `guiunittests`）。

## 根因分析
- **症状 A**：`std::mt19937_64` 引擎输出由 C++ 标准严格规定（跨 libstdc++/libc++ 一致）；但 `std::uniform_int_distribution` 把引擎值映射到 `[0,255]` 的算法是**实现定义**的。同一 seed 下两个标准库产生不同字节序列 → 基于它的硬编码期望值必在其中一个标准库下失败。
- **症状 B（CMake 特例陷阱，非通用机制）**：ctest 只运行被 `add_test()` 注册的测试。上游若只 `add_executable` 不 `add_test`，ctest 发现 0 个测试并退出 0 → **静默假绿（false-green）**：管道以为跑了上游测试，实则零执行。它**不是**所有构建系统的通性——Autotools 用 `make check`，Meson 用 `test()`，Rust/Go/Python 自动发现，都不受影响。

## 解决方案

### 推荐方案
- 症状 A：测试伪随机输入改为取引擎低字节 `mt19937_64 & 0xFF`（确定性、跨标准库一致），并同步更新期望值；不复用 `uniform_int_distribution`。
- 症状 B：**仅在 CMake 且上游测试目标未 add_test 注册时**，不要依赖 `cmake.test()`（会静默跑 0 测试）；改为在 `conanfile build()` 里 `can_run()` 守卫直接运行测试可执行文件并输出 `HMBS_UPSTREAM_TEST_RESULT` 标记。解析 gtest 输出时把 `[  FAILED  ]` / `[  PASSED  ]` 的方括号转义为 `\[ \]`（否则被当作正则字符类，导致误解析）。

### 禁止做法
- ❌ 症状 A：不要用 `dist(engine)`（`uniform_int_distribution`）作为测试伪随机输入——跨标准库输出不同字节序列。
- ❌ 症状 B：对未 add_test 注册的 CMake 测试目标盲目调用 `cmake.test()`/ctest——会静默跑 0 测试，掩盖上游测试未执行的事实，形成欺骗性 CI 通过。

## 验证
- 症状 A：在 OHOS(libc++) 下运行 unittests，`[  PASSED  ] 135 tests`，无 FAILED。
- 症状 B：`conan build()` 日志出现 `HMBS_UPSTREAM_TEST_RESULT={"status":"passed","discovered":135,"passed":135,"failed":0}`，证明测试被真实执行而非 0 测试逃生。

## 关联条目
- 相关: E239（Conan test_package 测试失败诊断保留）、E302（符号存在但行为契约破坏）
