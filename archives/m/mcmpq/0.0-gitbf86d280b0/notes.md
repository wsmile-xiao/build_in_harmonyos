# mcmpq 0.0-gitbf86d280b0 适配笔记

## 上游信息
- 上游仓库: https://github.com/173duprot/mcmpq.h (官方)
- 版本: 0.0-gitbf86d280b0 (commit bf86d280b067)
- 类型: 单头文件 C11 无锁 MPMC 队列库 (header-only, 无构建系统)
- 官方源码 URL: https://codeload.github.com/173duprot/mcmpq.h/tar.gz/bf86d280b067
- tarball SHA-256: 5cf7dd8340a6f4403d29eb589d348655542d0abf840a73f4a85ccb7e639f87b6
- mcmpq.h SHA-256: 7b956fadb57f109074cf61da69942e82e0df55d38edf73b9a58fe8ce6f23bbcc

## 上游测试枚举台账 (完整)
| 入口 | 类型 | 是否独立上游用例 | 是否运行 | 结果 | 说明 |
|------|------|----------------|---------|------|------|
| tests/basic.c | 用户测试源 (含 main) | 是 | 是 | 通过 (exit 0) | 8 线程 × 1000 项生产者/消费者，断言队列清空 |
| tests/fuzz.c | 用户测试源 (含 main) | 是 | 是 | 通过 (exit 0) | 4 线程 × 10000 项 × 1000 轮 (4000万项)，断言队列清空 |
| tests/a.out | 上游误提交的编译产物 | 否 | - | - | 二进制产物非源码，不计入独立用例 |

- 源码声明测试总数 (source_declared_total): 2
- 当前 OHOS 配置可执行用例数 (configured_executable_total): 2
- 实际执行并通过 (executed_passed_total): 2 (2/2 = 100%)
- 全量通过率: 2/2 = 100%
- 失败: 0; 未运行/未实例化: 0
- 映射: tests/basic.c (main) -> clang -O2 -pthread -> basic.ohos -> 实际执行日志 -> 通过
- 映射: tests/fuzz.c (main) -> clang -O2 -pthread -> fuzz.ohos -> 实际执行日志 -> 通过

## 鸿蒙专项测试
- test_package/ohos_specific_test.c（适配新增，随 test_package 作为真实源文件提交）：
  验证 try_enqueue/try_dequeue 返回语义、单生产者单消费者全链路、FIFO 顺序、
  队列 SLOTS 容量边界、HEAD/TAIL 一致性；18/18 断言通过 (exit 0)。
  编译/运行: clang -O2 -pthread test_package/ohos_specific_test.c（经 conan create
  test_package CMake 目标 test_ohos_specific），日志 SHA-256
  eb572b4c3d2bbbeca9284ef5293c583aabd6bb8dfc5a2af1d548e7909d2f5839

## 适配要点
- header-only 库，无需构建系统；conanfile.py 采用 header-only 模板
- 无需 commands.json (无 CLI 产物, R38)
---

**编译结束**: 2026-09-28 17:05
**最终状态**: published
