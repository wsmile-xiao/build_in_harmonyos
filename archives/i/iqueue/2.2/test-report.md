# iqueue 2.2 上游测试台账（双口径）

## 测试发现与统计口径

- 源码声明总数（`source_declared_total`）：12（src/test.c 中 main() 直接调用的独立测试函数：test_initfree、test_query、test_trysend_single、test_send_single、test_tryrecv_single、test_recv_single、test_close、test_iqsignal、test_multi_sendrecv、test_initfree1、test_query1、test_single_sendrecv1）
- 当前配置可执行总数（`configured_executable_total`）：12（单一测试程序 bin/iqueue_test 内的 12 个测试函数全部实例化执行）
- 实际执行并通过（`executed_passed_total`）：12
- 失败：0
- 未运行/不可运行/硬阻塞：0
- **全量通过率：12/12 = 100%**
- 当前配置可执行集合通过率：12/12 = 100%（补口径，不替代全量通过率）
- 断言统计：src/test.c 共 371 处 `TEST()` 断言；实测输出 49 个 PASS 标记（PASS 组标记，含循环内重复执行），全部通过（退出码 0）
- 依赖：仅 pthread（libc 内置），无外部 Conan 依赖，无因依赖未运行入口

## 枚举台账（源码声明 → 构建条件 → 构建目标 → 注册项 → 实际执行）

| 入口 | 源文件 | 分类 | 是否独立上游用例 | 构建目标 | 注册方式 | 实际执行 | 结果 |
|---|---|---|---|---|---|---|---|
| test_initfree | src/test.c:188 | 用户测试源 | ✅ | bin/iqueue_test | main() 第 1 项 | ./bin/iqueue_test | PASS（new/delete 全容量族 + 锁/条件变量交互 + EINVAL） |
| test_query | src/test.c:290 | 用户测试源 | ✅ | bin/iqueue_test | main() 第 2 项 | ./bin/iqueue_test | PASS |
| test_trysend_single | src/test.c:350 | 用户测试源 | ✅ | bin/iqueue_test | main() 第 3 项 | ./bin/iqueue_test | PASS |
| test_send_single | src/test.c:472 | 用户测试源 | ✅ | bin/iqueue_test | main() 第 4 项 | ./bin/iqueue_test | PASS |
| test_tryrecv_single | src/test.c:560 | 用户测试源 | ✅ | bin/iqueue_test | main() 第 5 项 | ./bin/iqueue_test | PASS |
| test_recv_single | src/test.c:688 | 用户测试源 | ✅ | bin/iqueue_test | main() 第 6 项 | ./bin/iqueue_test | PASS |
| test_close | src/test.c:799 | 用户测试源 | ✅ | bin/iqueue_test | main() 第 7 项 | ./bin/iqueue_test | PASS |
| test_iqsignal | src/test.c:913 | 用户测试源 | ✅ | bin/iqueue_test | main() 第 8 项 | ./bin/iqueue_test | PASS（含 100 线程 wait/signal） |
| test_multi_sendrecv | src/test.c:1076 | 用户测试源 | ✅ | bin/iqueue_test | main() 第 9 项 | ./bin/iqueue_test | PASS（多线程多队列） |
| test_initfree1 | src/test.c:1151 | 用户测试源 | ✅ | bin/iqueue_test | main() 第 10 项 | ./bin/iqueue_test | PASS |
| test_query1 | src/test.c:1228 | 用户测试源 | ✅ | bin/iqueue_test | main() 第 11 项 | ./bin/iqueue_test | PASS |
| test_single_sendrecv1 | src/test.c:1381 | 用户测试源 | ✅ | bin/iqueue_test | main() 第 12 项 | ./bin/iqueue_test | PASS |

### 非独立用例项（台账列出，不计入上游用例数）

| 入口 | 源文件 | 分类 | 说明 |
|---|---|---|---|
| TEST()/PASS() 宏 | src/test.c:18-33 | 框架宏 | 自定义断言宏（371 处 TEST），非独立用例 |
| example1-4.c | 根目录 | 样例 | 独立编译的示例程序，非测试 |
| thr_lock/thread_simulate_read/thread_call_send/thread_call_recv/thread_epipe_send/thread_epipe_recv/thread_callwaitsignal/thr_lock1 | src/test.c | 测试辅助线程 | 被测试函数驱动的辅助线程，非独立用例 |
| bin/iqueue_test_debug | Makefile | 同一测试的 debug 变体 | 同一 12 项用例，非新增用例 |

## 适配补丁（3 个，均为 OHOS 64 位平台可移植性修复）

1. `0001-test-glibc-malloc-stats-guard.patch`：test.c allocated_bytes() 的 GNU malloc_stats 扩展以 `__GLIBC__` 守卫；OHOS libc（musl 系）无该符号，走上游自带 `#else` 回退分支（返回 0）。
2. `0002-new-iqueue-uint32-overflow.patch`：new_iqueue() 的 aligned_capacity 在 64 位下可超过 uint32_t 范围，原 `uint32_t` 类型左移溢出为 0 导致 `new_iqueue((uint32_t)-1)` 死循环；改为 size_t 并对超大容量返回 EINVAL（与 32 位行为一致）。首错：test_initfree 第 4 段挂起（timeout 124）。
3. `0003-test-clearsignal-uint32.patch`：test.c clearsignal_iqsignal 循环计数用 `uint32_t`（与公开 API 返回类型一致），修复 64 位下 `size_t i` 超过 2^32 时的必然断言失败。首错：`src/test.c:953: TEST failed`。

## 逐项映射与执行证据

- 构建命令（cwd=`$BUILD_SRC_DIR`）：`make -j1 makedir iqueue` → `clang -Iinclude -std=c99 -O3 src/test.c bin/iqueue.a -lpthread -o bin/iqueue_test`，exit 0
- 运行命令（cwd=`$BUILD_SRC_DIR`）：`./bin/iqueue_test`，exit 0
- 运行日志：`/storage/Users/currentUser/tmp/iqueue-testlogs/iqueue_test4.out`，SHA-256 `878395ad0d4b14ae79c9f244e8e7faeb65df769a1d9804c5b5e090dcec9042c0`
- 输出：`Running iqueue test: .................................................`（49 个 PASS 标记），无 TEST failed，无 Memory leak

## 临时目录与环境恢复

- 无 `/tmp` 不可写问题（本任务全部使用 `$TMPDIR=/storage/Users/currentUser/tmp`，可写、可执行）。
- 无 LD_LIBRARY_PATH/动态库探测 skip（iqueue 纯静态库，仅依赖 libc+pthread）。
- 无因依赖未运行的上游入口；依赖复查：iqueue 无 requires（conanfile.py requirements() 为空），不涉及 registry 制品可用性查询。

## 结论

上游测试全量通过：12/12（100%），371 处断言全部通过。三个最小补丁（2 个测试侧可移植性 + 1 个库侧 64 位缺陷修复）已声明于 conandata.yml patches 并在本地 worktree 验证。
