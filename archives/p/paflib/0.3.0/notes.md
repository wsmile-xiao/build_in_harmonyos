# paflib 0.3.0 适配笔记（路径 C · 高难度挑战）

## 编译环境
- 构建系统：上游 autotools，本配方改为 **clang 直编**（绕过 configure/config.sub）
- 目标：OHOS aarch64（Conan `os=OHOS, arch=armv8`）
- 编译器：clang / 归档 llvm-ar（OHOS SDK）

## 上游形态

paflib 是 IBM 的 **Power 架构设施库**，暴露 DSCR / EBB / PPR / TB：

- 全部设施用 PowerPC 指令实现：`mfspr`/`mtspr`、`or Rx,Rx,Rx`、`rfebb`；
- `ebb/ebb-callback.S` 是 23 KB 的 PowerPC 汇编回调（EBB 硬件入口）；
- 上游 `configure.ac` 对非 `powerpc*/ppc*` 主机
  `AC_MSG_ERROR([Unsupported architecture/os])`——它在设计上就是 Power 专属。

## 适配策略（aarch64）

aarch64 与 Power 架构不同。适配原则：**能复现 API 语义的设施就做实**，
只有硬件确实无法替代的才降级。

| 设施 | aarch64 做法 |
|------|--------------|
| DSCR | **软件 DSCR 模型**：跳过 Power SIGILL 探针，用线程局部 `__thread uint64_t` 保存寄存器镜像，`paf_dsc_check_support()` 返回完整 `DSCR_ISA_2_07_MASK`；`paf_dsc_set/get` 的往返与越界 `EINVAL` 校验完全可用 |
| PPR | inline 帮助函数改为 no-op |
| TB   | `paf_timing_now()` 用 `clock_gettime(CLOCK_MONOTONIC)`（纳秒）替代 `mfspr 268/269` |
| EBB  | **仿真事件源**：OHOS 禁用 `perf_event_open`（见下），改用进程级 `setitimer(ITIMER_REAL)`+`SIGALRM`，周期取自请求的 sample period；触发时调用公开 API 注册的每线程 handler，完整实现 register/enable/disable/reset/close |

## 关键实测与问题

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `perf_event_open` 不可用 | OHOS 对 HW / SW / RAW 三类事件一律返回 `EACCES`（seccomp），即使 `/proc/sys/kernel/perf_event_paranoid=-1` | EBB 改用 `setitimer` 事件源（见补丁 0005） |
| 2 | POSIX `timer_create(SIGEV_SIGNAL, SIGRTMIN)` 挂起 | 实测设备上该路径不返回 | 改用进程级 `setitimer(ITIMER_REAL)`+`SIGALRM`（已实测可用） |
| 3 | `paf-common.h` 的 `mfspr/mtspr/sync` 无法在 aarch64 编译 | inline asm 是 PowerPC 指令 | 补丁 0001：`__powerpc__` 守卫 + 非 Power 回退（`mb()` → `__sync_synchronize()`） |
| 4 | `paf-hwcap.c` auxv 探测依赖 `<link.h>` | 非 Power 不需要（也无 Power 设施） | 补丁 0001：守卫 auxv walk |
| 5 | `dsc.c` 用 `ucontext_t` + `uc_mcontext.regs->nip` | DSCR 探针为 Power 设计 | 补丁 0002：软件 DSCR 模型 |
| 6 | `tb.h` 用 `mfspr 268/269` | 无 Time Base 寄存器 | 补丁 0003：`clock_gettime` 回退 |
| 7 | `ppr.h` 用 `or Rx,Rx,Rx` | 无 PPR/共享资源提示 | 补丁 0004：no-op |
| 8 | `ebb` 依赖 Power SPR / perf 原始 Power 事件 / 汇编 TCB 访问 | 无 EBB 设施且 perf 不可用 | 补丁 0005：`__powerpc__` 守卫 + 仿真事件源 |
| 9 | `ebb-init.c` 用 `<gnu/libc-version.h>` | OHOS bionic 无 glibc 专有接口 | 补丁 0005：平台分支，非 Power 固定用 TLS 保存区 |
| 10 | 上游 EBB 测试直接内联 Power SPR 汇编 / 依赖 Power 汇编 hook | 测试是 Power 硬件测试 | 补丁 0006：逐文件移植，保留 Power 原逻辑；仅 save-area 脚本跳过 |

## 测试口径

- **上游测试（13）**：`dsc/tests/test_dsc`、10 个 EBB 测试、`test_ebb_save_area_env.sh`、`tb/tests/test_tb`。
  - **aarch64 真实执行并通过 12 项**（含 10 个 EBB 测试实际触发回调）；
  - 仅 `test_ebb_save_area_env.sh` 跳过：它执行 libpaf-ebb 的 **Power-only `.interp` 版本入口**（`paf-interp.c`），
    非 Power 平台不构建该入口。
- **消费者测试**：`test_package/test_paflib.c`，19 项断言（含实际触发 EBB 回调）。

## 验证结果

```bash
# 真机 conan create（OHOS aarch64, clang 15.0.4, paflib/0.3.0@ohpcd/stable）
CREATE_RC=0
# 包 ID 6b129b068851896169fae42d399fa922d239ce8a

# 上游测试（build() 内实跑，12/13 执行并通过）
test_dsc                        -> exit 0（软件 DSCR：set/get 往返 + EINVAL 校验）
test_tb                         -> Time taken ... / Total time taken is 313 ticks  (exit 0)
test_ebb                        -> Enable/disable EBB (emulated) : ok              (exit 0)
test_ebb_pmu                    -> handler 触发 8 次（4 种 callback × 2）           (exit 0)
test_ebb_pmu_reset              -> handler 触发 3 次                               (exit 0)
test_ebb_backtrace              -> emulated EBB handler invoked                    (exit 0)
test_ebb_pmu_multi              -> handler 触发 2 次                               (exit 0)
test_ebb_pmu_clobber            -> 4 种类型各触发 5 次                              (exit 0)
test_ebb_child                  -> handler 触发 2 次                               (exit 0)
test_ebb_clear_on_close         -> handler 触发 2 次，close 后 timer 解除           (exit 0)
test_ebb_nohandler              -> exit 0（无 handler 时 enable/disable 安全）      (exit 0)
test_ebb_cpu                    -> handler 触发 2 次                               (exit 0)
test_ebb_save_area_env.sh       -> SKIP（Power-only .interp 版本入口）

# 消费者测试（test_package/test_paflib.c）
PASS x19, PAFLIB_CHECK_SUMMARY checks=19 fails=0

# 产物
lib/libpaf-dsc.a  lib/libpaf-ebb.a
include/paf/{dsc,ebb,ppr,tb}.h
share/man/man3/libpaf-{dsc,ebb,tb}.3  licenses/COPYING
```

- 上游测试：注册 **13**；执行并通过 **12**；平台跳过 **1**（`test_ebb_save_area_env.sh`，
  技术原因：Power-only `.interp` 入口）；失败 **0**。
- 新增消费者测试：**19/19（100%）**。

## 构建实现说明

- 采用 **clang 直编**（`build()` 内编译 `libpaf-dsc.a` / `libpaf-ebb.a` 并逐个编译运行上游
  测试），不用上游 autotools，避免 config.sub/config.guess 与 libtool 的坑。
- `config.h` 由配方生成（仅需 `PACKAGE_*` 宏）；不构建 `*-version.c`、`paf-interp.c`
  与 `ebb-callback.S`（后两者是 Power 专用的直接 DSO 入口/Power 汇编）。
- 编译带 `-Wno-unused-function`，因为非 Power 分支会移除部分用不到的静态函数。

## 注意事项

- EBB 在 aarch64 上是**仿真事件源**（interval timer），不是微架构 PMU 事件；
  handler、上下文、enable/disable/reset/period 等公开 API 语义完整，但触发时机是周期性的。
- DSCR 是软件寄存器模型：API 状态机完整，但不会影响内存预取硬件行为。
