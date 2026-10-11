# DRAFT-ohos-perf-event-open-denied-substitute-event-source：OHOS 禁用 perf_event_open，PMU 采样需替代事件源

- **来源**：paflib 0.3.0 OHOS aarch64 适配（2026-10-03，contrib-9274，分支 `feat/paflib-0.3.0`）
- **类别**：平台系统调用/硬件采样能力缺口（syscall / detection / runtime）
- **相邻条目**：E314（R 的 `ITIMER_PROF`/`SIGPROF` CPU 时间采样——**不同子族**，那是用 SIGPROF 做 CPU profiling；本条是 perf 系统调用被拦截后改用 `setitimer(ITIMER_REAL)` 做事件源）；E051（SIGSYS 拦截系统调用）；E303/E008/E496（同样报 EACCES，但属文件/socket 场景，机制不同）。

## 现象

在真机 OHOS aarch64 上，用 `syscall(__NR_perf_event_open, ...)` 打开三类事件：

| 事件 | 结果 |
|------|------|
| `PERF_TYPE_HARDWARE` / `PERF_COUNT_HW_INSTRUCTIONS` | `fd=-1`，`errno=13 (EACCES)` |
| `PERF_TYPE_SOFTWARE` / `PERF_COUNT_SW_CPU_CLOCK` | `fd=-1`，`errno=13 (EACCES)` |
| `PERF_TYPE_RAW` / `0x11` | `fd=-1`，`errno=13 (EACCES)` |

而内核参数看起来是"允许"的：

```
/proc/sys/kernel/perf_event_paranoid = -1
/proc/sys/kernel/perf_event_max_sample_rate = 10000
```

`paranoid=-1` 极易误导——它通常意味着用户态可自由使用 perf，但 OHOS 的运行时
（seccomp/安全策略）在**系统调用入口**就把它拦掉了。因此这不是权限位/参数问题，
调参、加 CAP 都没用。

## 根因

OHOS 拦截 `perf_event_open`，用户态无法打开任何硬件性能计数器 → 依赖 PMU 采样
或 PMU 溢出中断的功能（采样 profiler、EBB 事件跳转等）无法按原方式实现。

## 替代事件源（实测可用性）

| 方案 | OHOS 实测 |
|------|-----------|
| `setitimer(ITIMER_REAL)` + `SIGALRM` | **可用** |
| `timer_create(SIGEV_SIGNAL, SIGRTMIN)` | **挂起（不可用）** |
| `perf_event_open`（HW/SW/RAW） | EACCES |

## 处置（把"事件分发"从"硬件事件源"解耦）

对依赖 PMU 的库：保留它面向用户的**handler 注册、enable/disable、上下文、
生命周期、period** 等 API，只替换最底层的事件来源：

1. 先做能力探测：读 `perf_event_paranoid`，再分别用 HW/SW/RAW 三类事件试探，
   若三类都 `EACCES` → 判定平台级不可用（避免误判为权限问题）。
2. 用 `setitimer(ITIMER_REAL)` + `SIGALRM` 作为事件源，周期由调用方请求的采样周期映射；
   信号处理器里调用该线程注册的 handler（含其 context），尊重 enable/disable；
   close 时解除定时器。**不要**用 `timer_create(SIGRTMIN)`（挂起）。
3. `__powerpc__` 等架构专属的原实现用宏守卫保留，Power 上行为不变。
4. 文档如实说明：触发是周期性的，**非微架构事件**。

## 验证证据（paflib EBB 仿真）

```
# 裸探针（真机 OHOS aarch64）
HW_INSTRUCTIONS fd=-1 errno=13(Permission denied)
SW_CPU_CLOCK    fd=-1 errno=13(Permission denied)
RAW_0x11        fd=-1 errno=13(Permission denied)
ITIMER_REAL_count=5                      # setitimer/SIGALRM 可用

# paflib 适配后，上游 EBB 测试真实触发回调并通过
test_ebb_pmu          -> handler 触发 8 次
test_ebb_pmu_reset    -> handler 触发 3 次
test_ebb_pmu_clobber  -> 4 种类型各触发 5 次
test_ebb_child        -> handler 触发 2 次
（上游 13 项注册：12 项真实执行并通过、1 项平台跳过，失败 0）
```

## 禁止做法

- 假设 `perf_event_open` 可用 / 只靠调 paranoid 或加 capability；
- 用 `timer_create(SIGRTMIN)`（OHOS 挂起）；
- 直接读 `mfspr`/`rdpmc` 等绕过 perf；
- 未做能力探测就把 EACCES 误判为"权限不足/代码 bug"。
