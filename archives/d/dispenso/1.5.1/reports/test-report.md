# Dispenso 1.5.1 测试报告

## 测试范围

- 官方源码: `v1.5.1`，SHA-256
  `e75b2a1bd428b2e9558ea99c03d266d2bf8881ba41689016e8c98052e1a0c17d`
- 目标平台: HarmonyOS 6.0 aarch64
- 工具链: OHOS Clang 15.0.4、CMake 4.2.3、Conan 2.29.1
- 上游框架: GoogleTest 1.17.0，经 CTest 执行

## 上游测试清点

上游 `tests/` 的 30 个 `*test.cpp` 共清点出 1109 个 GoogleTest 用例。
其中 `tests/CMakeLists.txt` 将 27 个测试翻译单元实例化为 1080 个
`unittest` 标签用例，并把 `priority_test.cpp` 与
`timed_task_test.cpp` 的 19 项人工诊断用例标为 `flaky`；另有 10 项在上游
稳定构建配置下未实例化或注册（包括上游明确未接入 CMake 的
`shared_pool_test.cpp`）。上游官方自动化主流程使用 `ctest -LE flaky`，
本适配保留全部 1109 项上游测试源码，并按同一稳定测试边界执行，没有修改
或删除任何上游测试用例。

## 执行结果

完整上游测试清点为 1109 项；官方稳定自动化执行集合为 1080 项，其余
29 项未进入该集合（19 项由上游标记为 `flaky`，10 项未由上游稳定配置
实例化或注册）。静态库与共享库配置下，稳定集合均为 1080/1080 通过。

| 配置 | 编译 | 上游稳定套件 | 消费端测试 | HarmonyOS 专项测试 |
|------|------|--------------|------------|--------------------|
| OHOS armv8 Release，静态库 | 通过 | 1080/1080（100%） | 1/1（16/16 检查） | 1/1（5/5 检查） |
| OHOS armv8 Release，共享库 | 通过 | 1080/1080（100%） | 1/1（16/16 检查） | 1/1（5/5 检查） |

消费端通过安装后的 Conan 包和 `Dispenso::dispenso` 目标，真实调用版本
宏、`ThreadPool`、`TaskSet`、`parallel_for` 与
`ConcurrentVector`。首次验证发现并修正了内嵌 concurrentqueue 的公开
包含目录导出问题，最终静态与共享两种包形态均通过。

异常路径测试调度抛出 `std::logic_error` 的任务并验证 `TaskSet::wait()`
精确重抛；串行 pipeline 阶段抛出 `std::runtime_error`，验证异常由头文件
实现在消费者模块中重抛。深度保护测试提交 96 项串行 continuation，确认
全部完成且观测到的内联深度达到、但不超过共享上限 32。

HarmonyOS 专项测试由 Conan 的 `settings.os=OHOS` 显式传给 CMake 后生成，
并要求编译器定义 `__OHOS__`，避免不同工具链对 `CMAKE_SYSTEM_NAME` 的映射
差异漏掉测试。测试将 64 个 Dispenso 任务提交给 `ThreadPool`，在实际工作
线程中通过 `pthread_self` 和 `pthread_getschedparam` 读取 OHOS libc 线程
调度信息，验证任务执行完整性及平台线程 ABI 交互。

共享库首次复测暴露了 Clang 跨 DSO 异常处理与线程局部状态分离的问题，
pipeline 异常安全用例因此持续自旋。回移上游官方提交 `68b6dc3` 与
`3a1aaa4` 的相关修改后，异常改在 catch 所在模块捕获为 `exception_ptr`，
递归深度 TLS 统一由库内导出访问器管理；另由头文件实现的 pipeline 在
调用方模块完成重抛。上游测试源码未改动。

## 仓库门禁

- `python3 -X utf8 tests/run_all.py`: 11/11 suites，全部通过。
- Python 配方语法与 YAML 解析: 通过。
- 官方源码 URL 与 SHA-256: 通过 Conan 下载、解压和校验。
- Git 改动范围: 仅 `archives/d/dispenso/1.5.1/`。

## 结论

编译、上游官方自动化套件、独立消费端 API 测试、HarmonyOS 专项测试及
仓库测试均全部通过。
