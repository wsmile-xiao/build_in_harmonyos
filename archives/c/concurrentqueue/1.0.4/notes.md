# concurrentqueue 1.0.4 — Bootstrap 笔记（pc3-36）

## 来源核验（bootstrap 阶段，官方资料确认）
- 官方仓库：https://github.com/cameron314/concurrentqueue
- 正式标签：`v1.0.4` → commit `6dd38b8a1dbaa7863aa907045f32308a56a6ff5d`
- Release 发布时间：2023-06-19T20:48:22Z（非 prerelease / draft）
- 许可证：Simplified BSD License（BSD-2-Clause）
- 源码 tarball：`https://github.com/cameron314/concurrentqueue/archive/refs/tags/v1.0.4.tar.gz`
- SHA-256：`87fbc9884d60d0d4bf3462c18f4c0ee0a9311d0519341cac7cbd361c885e5281`

## 结构
- header-only C++11：主头文件 `concurrentqueue.h` + `blockingconcurrentqueue.h` + `lightweightsemaphore.h` + `internal/`
- CMake INTERFACE library：目标 `concurrentqueue::concurrentqueue`，包/CMake 名 `concurrentqueue`
- 头文件安装到 `include/concurrentqueue/moodycamel/`（下游 include 为 `"moodycamel/concurrentqueue.h"`）
- 上游 CMake 无测试 target；测试用 `tests/unittests/` 的 makefile 独立构建（minitest.h 框架）
- 上游无 Conan 配方；bootstrap 阶段按 Conan 2.x 新建

## 依赖
- 无任何第三方依赖（仅 C++11 标准库 + pthread 用于线程测试）

## 首轮 Adapt / 本地验证
- 待执行：clang++ 编译 test_package smoke test + 上游 unittests makefile 测试
---

**编译结束**: 2026-08-30 08:07
**最终状态**: built
