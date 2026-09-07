# mapbox-variant 1.2.0 适配记录

- 类型：纯 header-only C++11/C++14 库，无外部 Conan 依赖。
- 上游测试：`make -j2 test` 构建 18 个翻译单元，运行 90 个 Catch 测试用例；
  `scripts/run_compilation_failure_tests.sh` 验证 7 个预期编译失败用例。
- 适配边界：只复制 `include/mapbox/*.hpp`，不把上游 Makefile 的
  `-march=native` 带入 OHOS 配方；测试 consumer 通过 `mapbox::variant`
  CMake interface target 验证真实 API。
