# OHOS sigwaitinfo 不填充 si_fd + F_SETSIG close 通知不可靠（事件监控线程挂起）

> 来源：libkqueue 2.6.1 第一轮适配（OHOS PC arm64），草稿编号 DRAFT-libkqueue-2.6.1-ohos-sigwaitinfo-si-fd-monitor

## 问题

在 OHOS（musl libc + Linux 内核）上，用户态事件库常用的"fd close 通知"模式失效：

1. **si_fd 恒为 0**：对 fd 设置 `O_ASYNC` + `F_SETSIG(SIGRTMIN+N)` 后由监控线程
   `sigwaitinfo` 等待，返回的 `siginfo_t.si_fd` 始终为 0（不填充被关闭的 fd）。
   依赖 `info.si_fd` 索引 `fd_map` 的清理逻辑永远找不到目标对象，kqueue 等
   资源永不释放，监控线程永不退出。
2. **close 通知偶发不投递**：关闭 fd 触发的 RT 信号并非每次都送达监控线程，
   部分运行中监控线程在 `sigwaitinfo` 永久等待。
3. **无 pthread_cancel + join 永久阻塞**：OHOS sysroot libc（musl）不导出
   `pthread_cancel`/`pthread_setcancelstate`/`pthread_testcancel`
   （`nm -D <sysroot>/libc.so | grep pthread_cancel` 0 命中），进程退出清理
   路径 `pthread_cancel + pthread_join` 无法取消线程，且对已自 detach 的
   线程执行 `pthread_join` 在 OHOS musl 上**永久阻塞**，进程挂起。

### 复现

```c
int kq = kqueue();      /* 内部创建监控线程，sigwaitinfo 等 close 通知 */
close(kq);              /* 触发 F_SETSIG RT 信号（偶发不达） */
return 0;               /* exit -> atexit -> join 监控线程 -> 挂起 */
```

实测现象：偶发卡死在进程退出阶段；`/proc/<pid>/task/*/wchan` 显示
主线程 `FUTEX`（join）、监控线程 `signalmgr_timedwait`（sigwaitinfo 等待）。

## 根因

- OHOS musl 的 `sigwaitinfo` 对 F_SETSIG 投递的 RT 信号不填充 `si_fd`；
- close 触发信号的投递在 OHOS 上存在竞态/不可靠；
- libc 不实现 POSIX 线程取消扩展符号，且对已 detach 线程的 join 语义异常。

## 方案（libkqueue 2.6.1 实测有效，3 个补丁叠加）

1. **si_fd 无效时退化为全量扫描**：`monitoring_thread_kqueue_cleanup(signal_fd)`
   中 `fd_map[signal_fd] < 0` 时（si_fd 无效场景），遍历 `kq_list`，对
   `fcntl(kq->kq_id, F_GETFD)` 返回 `-1/EBADF`（fd 已关闭）的对象执行清理。
2. **监控线程 sigtimedwait 轮询**：`sigwaitinfo` 改为 `sigtimedwait`（100ms 超时）；
   每次 `EAGAIN` 超时主动扫描活跃 fd 关闭状态，扫描后无存活对象即退出循环。
   注意 break 时保持 `kq_mtx` 持有（退出路径会解锁），避免锁计数失衡。
3. **退出路径显式唤醒 + 跳过 join**：`linux_libkqueue_free` 中
   `pthread_cancel` 返回 ESRCH 时用
   `tgkill(SYS_tgkill, getpid(), monitoring_tid, MONITORING_THREAD_SIGNAL)`
   显式唤醒监控线程；OHOS 分支跳过 `pthread_join`（线程已自行 detach 退出，
   join 在 musl 上永久阻塞），进程退出时由 OS 回收。

libc 探针统一用 `__OHOS__`（该工具链未定义 `__MUSL__`）。

## 验证

- `conan create . -pr:h=ci/conan/profiles/ohos-aarch64` → EXIT=0，test_package
  打印 `OK: kqueue() = 5` 后正常退出（修复前偶发 SIGTERM 挂起）；
- 复现程序（kqueue→close→exit）修复后 15/15 稳定退出；
- 鸿蒙专项测试（EVFILT_READ/TIMER/USER 真实语义）15/15 PASS。

## 适用边界与反例

- 适用：OHOS/OpenHarmony 上任何使用 `F_SETSIG + sigwaitinfo` 监听 fd close
  的事件机制，或依赖 pthread_cancel 清理工作线程的库。
- 反例：glibc/Linux 上 sigwaitinfo 会正确填充 si_fd，信号投递可靠，原逻辑可用；
  若工具链定义 `__MUSL__` 且符号可探测，应优先按 DRAFT-ohos-pthread-cancel-decl
  逐符号 nm 探测决定声明型还是 stub 方案。

## 关联

- similar_to / caused_by：DRAFT-ohos-pthread-cancel-decl（pthread 取消符号层面）、
  E085（musl 不实现 pthread cancel）、E127（HarmonyOS 声明缺失）
- 本条目补充：信号语义层面（si_fd 恒 0、close 通知不可靠、join 阻塞）

## 证据

- 补丁：`archives/l/libkqueue/2.6.1/patches/0003/0004/0005`
- 日志：`archives/l/libkqueue/2.6.1/reports/`（knowledge-ledger.md、ohos_specific_test 输出）
- conan create13 EXIT=0
