# DRAFT-sml-1.1.11 — 上游 Makefile 固定 -fno-exceptions 时改用 CMake/ctest 规范路径

> 触发事件: sml 1.1.11 HarmonyOS PC 正式适配（R01, pc2-43）
> 库类型: header-only C++14 状态机库（boost-ext/sml）

## 问题

sml 上游同时提供两套测试入口：

- `Makefile` 的 `test` 目标：对 clang++/g++ 分支**固定**追加
  `DISABLE_EXCEPTIONS=-fno-exceptions`（所有 test 目标共用 CXXFLAGS）
- `CMakeLists.txt` + `ctest`：`SML_USE_EXCEPTIONS` 选项**默认 ON**，与上游
  CI（build_matrix.yml）同源

执行 `make test` 时，`test/ft/actions_defer.cpp` 依赖的
`test/ft/static_deque.h` 内部使用 `throw std::out_of_range(...)` /
`throw std::runtime_error(...)`，clang 在 `-fno-exceptions` 下直接报硬错：

```
test/ft/static_deque.h:27:7: error: cannot use 'throw' with exceptions disabled
      throw std::out_of_range("queue is empty");
...
7 errors generated.
make: *** [Makefile:48: test/ft/actions_defer.out] Error 1
```

## 根因

这是**上游 Makefile 的全局开关设计**，不是库本体缺陷，也不是配方缺陷：

1. Makefile 为 clang++/g++ 统一加 `-fno-exceptions`（减少生成代码），
   但 actions_defer（defer 队列测试）依赖异常语义；
2. 同一套测试经 CMake 路径（`SML_USE_EXCEPTIONS=ON` 默认）完整编译运行；
3. 上游 CI 本身就走 CMake + ctest，`make test` 只是开发辅助入口。

## 方案

采用与上游 CI 同源的 CMake/ctest 路径运行上游测试，并如实申报：

```bash
cmake -S . -B build -DSML_BUILD_TESTS=ON -DSML_BUILD_EXAMPLES=OFF \
      -DSML_BUILD_BENCHMARKS=OFF -DCMAKE_BUILD_TYPE=Release
cmake --build build -j2
ctest --test-dir build --output-on-failure
```

## 验证

- ctest 30/30 全部通过（0 失败，100%）：ft 功能测试 + ut 工具测试 + unit 单元测试
- `test/ft/errors/` 4 项预期编译失败测试未注册 ctest，按预期行为记录
- conan-verify（G0-G4 + L2/L4/L5）PASS；W3 本地 CI（build_and_test.sh）
  1/1 通过；test_package 消费者测试（真实调用 sml API 断言状态迁移）PASSED

## 适用边界

- 上游**同时提供** Makefile 测试目标（对 clang++/g++ 全局 -fno-exceptions）
  与 CMake 测试入口（默认启用异常）的库；
- header-only / 模板库尤常见（Makefile 常为辅助入口）；
- 若上游只有 Makefile 且确实需异常测试，则按库实际能力评估，不套用本方案。

## 反例

- 上游 Makefile 未固定 -fno-exceptions：直接 `make test` 即可，无本问题；
- `-fno-exceptions` 下**所有**测试都失败（非个别异常依赖测试）：
  属于库对异常编译的普遍不兼容，需另行评估，不能简单归为路径选择。

## 限制

- 测试统计以 ctest 实测为准（R51），Makefile 路径的失败必须记录原因与依据，
  不得隐瞒或伪造；
- 本条目不改变任何编译/配方结论，仅规范"两套测试入口不一致时如何选依据"。
