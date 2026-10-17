# PAFLib — IBM Power Architecture Facilities Library

`paflib` 是 IBM 编写的库，把 **Power 架构硬件设施**从用户态以 API 形式暴露：

- **DSCR**（Data Stream Control Register，数据流控制寄存器）
- **EBB**（Event-Based Branching，基于事件的跳转，POWER8 / ISA 2.07）
- **PPR**（Program Priority Register，程序优先级寄存器）
- **TB**（Time Base，时基寄存器）

## 上游形态

- 上游仓库：<https://github.com/paflib/paflib>，tag `0.3.0`（MIT）。
- 全部实现都依赖 PowerPC 指令：`mfspr`/`mtspr`（SPR 读写）、`or Rx,Rx,Rx`
  （PPR/锁提示）、`rfebb`，以及 `ebb/ebb-callback.S` 的 23 KB PowerPC 汇编回调。
- 上游 `configure.ac` 对任何非 `powerpc*/ppc*` 主机直接 `AC_MSG_ERROR`。

## OHOS 适配要点（路径 C · 高难度挑战）

目标是 **aarch64 / OHOS**，与 Power 架构完全不同。移植不是「一律返回不支持」，
而是**能复现的 API 语义就做实**，只有硬件确实无法替代的才降级：

| 设施 | aarch64 现实 | 适配做法 |
|------|--------------|----------|
| DSCR | 无该寄存器 | **线程局部软件 DSCR 模型**：暴露完整 ISA 2.07 掩码，`paf_dsc_set/get` 的往返与越界校验完全可用 |
| PPR  | 无对应寄存器 | inline 帮助函数降级为无副作用 no-op |
| TB   | 无 Time Base 寄存器 | `paf_timing_now()` 回退 `clock_gettime(CLOCK_MONOTONIC)`（纳秒），保持单调 tick 语义 |
| EBB  | 无 EBB 设施；且 `perf_event_open` 对所有事件类型返回 `EACCES`（seccomp），硬件 PMU 不可用 | **可用的仿真事件源**：进程级 `setitimer(ITIMER_REAL)`+`SIGALRM`，周期取自请求的 sample period；触发时调用公开 API 注册的每线程 handler，完整实现 `register_handler`/`enable_branches`/`disable_branches`/`pmu_reset`/`event_close` |

- 所有 Power 专属代码用 `#if defined(__powerpc__) || defined(__powerpc64__)`
  守卫，Power 分支原样保留。
- `common/paf-common.h` 的 `mfspr/mtspr/sync` 增加非 Power 回退（`mb()` →
  `__sync_synchronize()`）。
- 避免 glibc 专有接口：`<gnu/libc-version.h>` 与 glibc TCB EBB 字段在
  OHOS bionic 上不存在，改为平台分支并使用 TLS 保存区。
- **测试**：上游 `make check` 注册 13 个测试。其中 **12 个在 aarch64 真实执行并通过**
  （含 10 个 EBB 测试实际触发回调）；仅 `test_ebb_save_area_env.sh` 因依赖
  Power-only 的 libpaf-ebb `.interp` 版本入口而跳过（有明确技术原因）。

## 产物

| 路径 | 说明 |
|------|------|
| `lib/libpaf-dsc.a` | DSCR 设施库（aarch64 软件模型，API 完全可用） |
| `lib/libpaf-ebb.a` | EBB 设施库（aarch64 仿真事件源驱动回调） |
| `include/paf/dsc.h` | DSCR 公开头 |
| `include/paf/ebb.h` | EBB 公开头 |
| `include/paf/ppr.h` | PPR 公开头（header-only） |
| `include/paf/tb.h` | Time Base 公开头（header-only） |

## 参考资料

- 上游仓库：<https://github.com/paflib/paflib>
- 许可证：MIT
