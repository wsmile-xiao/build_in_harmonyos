# benchmark 1.9.5 适配笔记

## 范围

- 软件：`benchmark` 1.9.5（Google Benchmark）
- 分支：`feat/benchmark-1.9.5`
- 构建系统：CMake + C++17
- 上游主页：<https://github.com/google/benchmark>
- 源码归档：`https://github.com/google/benchmark/archive/refs/tags/v1.9.5.tar.gz`
- SHA-256：`9631341c82bac4a288bef951f8b26b41f69021794184ece969f8473977eaa340`

## 配方设计

- 包类型为 `library`，默认静态库；`shared`/`fPIC` 选项与上游 `BUILD_SHARED_LIBS` 保持一致。
- 上游安装 `benchmark` 与 `benchmark_main` 两个库，分别导出为
  `benchmark::benchmark` 和 `benchmark::benchmark_main`；后者依赖前者。
- 上游 GTest 测试通过已发布的 `gtest/1.17.0.1` 组件配方接入，并固定
  `BENCHMARK_USE_BUNDLED_GTEST=OFF`、`BENCHMARK_DOWNLOAD_DEPENDENCIES=OFF`，避免
  在构建阶段联网下载或混入未声明的 bundled GTest。该依赖只用于配方构建测试。
- 关闭文档、Python tools 和仅面向 x86_64/FileCheck 的汇编测试；保留上游 CTest
  非 GTest 测试与 GTest 测试。
- 未修改上游源码，因此 `patches/` 只保留说明文件。

## OHOS 消费者兼容性测试

`test_package` 编译两个真实消费者：

1. `test.cpp` 链接 `benchmark::benchmark`，注册并执行一个 benchmark，并检查
   `RunSpecifiedBenchmarks()` 返回一个匹配项。
2. `test_main.cpp` 链接 `benchmark::benchmark_main`，通过上游 `BENCHMARK_MAIN()`
   入口执行 benchmark。

两个程序均使用 `--benchmark_min_time=0.001s`，避免测试等待不可控的基准运行时。
它们在 OHOS 设备上完成编译和运行，覆盖两个导出组件的消费者链接与运行路径，
计为 2 个 OHOS 消费者兼容性用例。

## 设备验证记录

设备端上游 `ctest --output-on-failure` 共 84 项，84 项通过、0 项失败，退出码为 0。
设备端 `conan create` 完成干净构建并生成 `libbenchmark.a` 与
`libbenchmark_main.a`；`test_package` 的 `test_benchmark` 和
`test_benchmark_main` 均完成编译和运行。该版本当前状态为 `built`，仅表示设备端
构建和验证完成，不表示已发布。

---

**编译结束**: 2026-09-09 19:51
**最终状态**: built

macOS 侧只进行配方、路径、SHA-256 和 Python 静态检查，不把 macOS 结果作为 OHOS
编译或运行证据。
