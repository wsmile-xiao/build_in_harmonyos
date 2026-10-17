# thread-pool 4.1.0 — 适配笔记（OHOS aarch64）

## 来源核验
- 官方仓库：https://github.com/bshoshany/thread-pool
- 正式标签：`v4.1.0`（git tag 指向 commit `097aa718f25d44315cadb80b407144ad455ee4f9`）
- 源码 tarball：`https://github.com/bshoshany/thread-pool/archive/refs/tags/v4.1.0.tar.gz`
- SHA-256：`be7abecbc420bb87919eeef729b13ff7c29d5ce547bdae284923296c695415bd`（tarball 实测）
- 许可证：MIT（LICENSE.txt，Copyright (c) 2021-2026 Barak Shoshany）
- 包名说明：同上游 5.0.0/5.1.0 已归档为 `archives/b/bshoshany-thread-pool/`（沿用当时任务包名）；本任务按智能任务平台任务名（任务 7264）`thread-pool/4.1.0` 归档于 `archives/t/thread-pool/`，conan name 与平台任务名一致

## 结构
- v4.1.0 为头文件库：`include/BS_thread_pool.hpp`（主头，线程池 + multi_future）+ `include/BS_thread_pool_utils.hpp`（独立工具类 BS::synced_stream / BS::signaller，主头不包含它）
- 无任何构建系统（tarball 无 CMakeLists/configure/scripts/compile_cpp.py——compile_cpp.py 为 5.x 才引入）
- C++17/20 兼容；版本以宏 `BS_THREAD_POOL_VERSION_MAJOR/MINOR/PATCH` = 4/1/0 声明（v4 无 `BS::thread_pool_version` 版本对象，5.x 才有）
- 依赖：无任何第三方依赖（仅标准库）

## 与 5.x 归档的关键差异（为何无补丁）
- 5.x 的 OHOS 补丁（archives/b/bshoshany-thread-pool/5.1.0/patches/0001-ohos-thread-affinity-sched.patch，知识 E211）针对 **5.x 新增的原生线程亲和性扩展**（`pthread_getaffinity_np/pthread_setaffinity_np`）
- v4.1.0 头文件 `grep -c affinity` = 0 处，不引用任何 `pthread_*_np` 符号 → **无需补丁，未修改任何上游文件，patches/ 为空**

## 上游测试（四维账本）
- 测试文件：`tests/BS_thread_pool_test.cpp`（单文件，自带 check() 计数框架，非第三方测试框架；上游无 CTest/make check 注册层）
- **N_static（静态声明）= 87**：按 `check(` 调用点逐项统计（`grep -cE '^\s*check\('`；156/176 两行为 `void check(` 定义不计入，`check_constructor` 等辅助函数名不误计）
- **N_executed（实际执行）= 172**：运行日志 `SUCCESS: Passed all 172 checks!`——部分 check 位于按线程数/块数展开的循环中，运行期断言次数多于静态调用点，两口径分别记录不混算
- **失败/跳过 = 0/0**
- 验证矩阵（设备实测，clang 15.0.4 OHOS，`clang++ -std=c++XX -O2 -Iinclude tests/BS_thread_pool_test.cpp`）：

| 轮次 | 配置 | 编译 | 运行 | 结果 |
| --- | --- | --- | --- | --- |
| 1 | C++17 | OK（rc=0） | rc=0 | `SUCCESS: Passed all 172 checks!` |
| 2 | C++20 | OK（rc=0） | rc=0 | `SUCCESS: Passed all 172 checks!` |

- 原始日志：设备 `~/tmp/uc2/thread-pool-4.1.0/dl/src410/thread-pool-4.1.0/run_c17.log`、`run_c20.log`（编译 `compile_c17.log`/`compile_c20.log` 无告警）

## 语言预检
`ohc-run.py lang-preflight` 判定 cpp 匹配通过（milestone=lang_checked），任务声明语言 cpp 与源码主语言一致。

## 路径 B 判断（结论：不走 B，纯路径 A）
- 本任务零补丁、零上游文件修改、构建流程零报错，未产生新的错误签名；
- 同上游 5.1.0 已沉淀的跨库知识（E211 sched_*affinity 替换、OHOS Python platform.system() 事实）本任务未触发、无增量；
- 无新的可跨仓库复用知识，不满足路径 B 证据门槛，按纯路径 A 交付。

## test_package（消费者验证）
- Conan L1：CMakeDeps + find_package 链接打包头文件，消费者程序 `test_thread_pool.cpp`（1 个程序，6 项断言）：
  1. `submit_task` + future `get()` 返回 42；
  2. `detach_loop` 1000 次迭代 + `wait()` 计数一致；
  3. `submit_blocks` 返回 `BS::multi_future<int>`，等待并汇总各块结果 = 0..99 求和 4950；
  4-6. 版本宏 MAJOR/MINOR/PATCH = 4/1/0。
- 同时包含并使用独立工具头 `BS_thread_pool_utils.hpp`（`BS::synced_stream`），覆盖两个头文件的打包完整性；
- 消费者以 C++17 编译，`test()` 经 bash 包装执行二进制（OHOS mksh 无法直接 exec 的既有规避模式），失败以非零退出码判定。

## 后续
- 状态：built（2026-09-12 finish 收尾，内嵌 conan-verify 与 W3 本地 CI 模拟通过）
- 无 commands.json（纯库，无命令行产物）
---

**编译结束**: 2026-09-12 01:29
**最终状态**: built
