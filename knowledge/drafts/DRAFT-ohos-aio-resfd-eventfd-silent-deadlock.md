# OHOS 内核 AIO RESFD 通知静默失效（eventfd 永不唤醒）

## 现象

- 依赖 Linux AIO + eventfd 完成通知的库（Linux AIO kernel interface `io_submit` + `IOCB_FLAG_RESFD`），在 OHOS 上异步文件操作**永久挂起**，无错误日志（静默死锁）。
- 实测案例：sogou workflow 1.1.0 的 `IOService_linux.cc`（io_set_eventfd + poller `PD_OP_EVENT`），`WFFileIOTask` 上游测试 1800s 超时。

## 根因

OHOS 内核（musl libc）实现了 `io_setup`/`io_submit`/`io_getevents`（syscall 正常，数据读写正确），**但 `IOCB_FLAG_RESFD` 的 eventfd 完成通知路径无效**：

- `io_submit` 携带 resfd 的 iocb 成功返回（=1）
- 内核**不会向 eventfd 写完成计数**
- `epoll_wait(event_fd)` 永不唤醒（超时返回 0）
- 且 `io_submit` 不返回错误——静默性极强

独立 syscall 复现程序验证（对照组）：
- 不带 resfd 的 io_submit + io_getevents：✅ 正常
- eventfd + epoll（手写）：✅ 正常
- io_submit + IOCB_FLAG_RESFD + epoll_wait(event_fd)：❌ 永不唤醒

**只有 AIO RESFD 通知这一条链路坏**，eventfd/epoll/pipe 本身都正常。

## 修复方案

1. **优先用库自带的 AIO 备胎**：成熟库多有非 Linux 平台的线程池模拟层
   - workflow：`IOService_thread.cc`（pthread + pipe + `PD_OP_NOTIFY`），接口与 linux 版完全一致（IOSession prep_pread/pwrite/preadv/pwritev/fsync）
2. **切换宏必须全局定义**（关键坑）：
   - 若两套实现是**不同的类布局**（workflow 的 IOService_linux.h 与 IOService_thread.h 成员不同：io_ctx/event_fd vs pipe_fd[2]/maxevents），宏只定义在子目录（kernel/CMakeLists 的 add_definitions）时，**不同翻译单元看到不同类布局** → vtable/字段错乱
   - 实测症状：`Communicator::io_bind` 写 `service->pipe_fd[0]` 写进 io_ctx 指针字段 → 读出垃圾负数 fd（如 -144753984）→ mpoller_add 失败；`std::mutex` try_lock 假性失败（字段错位）
   - 诊断手段：try_lock 探测 + 打印对象地址与 `sizeof(std::mutex)`
   - 正确做法：顶层 CMakeLists `add_definitions(-DWORKFLOW_USE_THREAD_IOSERVICE)`
3. **消费者传导**：安装头若含条件 include 选择（Communicator.h 按 `__linux__ && !WORKFLOW_USE_THREAD_IOSERVICE` 选 IOService 头），`package_info().cpp_info.defines` 必须导出切换宏，否则消费者编译时 include 错误版本头（安装包只装了 thread 版）
4. **CMake 联动文件**（workflow 案例）：kernel/CMakeLists（源文件选择）、CMakeLists_Headers（安装头清单）、两份 Communicator.h（kernel/ + include/workflow/ 双拷贝）、Communicator.cc（io_bind/io_unbind/shutdown_io_service 分支）——全部用同一宏判定

## 检测方法（预扫描）

源码含 `IOCB_FLAG_RESFD` / `io_set_eventfd` / `io_setup(` 即应预警本条。

## 验证

workflow/1.1.0（task #7331）：thread 版 IOService 切换后，上游 38 测试 37 通过
（含 2 个文件 IO 测试 WFFileIOTask/WFFilePathIOTask），test_package HTTP 回环通过。
