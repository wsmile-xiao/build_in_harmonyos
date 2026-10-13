# DRAFT-cpp-ipc-1.3.0-futex-requeue-pi-trylock-pi-enosys

> 机制一句话：**OHOS/HongMeng 内核没有实现 futex 的 `FUTEX_CMP_REQUEUE_PI` / `FUTEX_WAIT_REQUEUE_PI` / `FUTEX_TRYLOCK_PI`
> 三种操作（`syscall(SYS_futex)` 直接 `errno=38 ENOSYS`），凡把跨进程条件变量建立在 PI-requeue 上的实现，
> `broadcast`/`wait` 全部失败；基础 `FUTEX_WAIT` / `FUTEX_WAKE` / `FUTEX_LOCK_PI` / `FUTEX_UNLOCK_PI` 正常。**
>
> 触发实例：`cpp-ipc 1.3.0`（共享内存 IPC 库，`src/libipc/platform/linux/a0/` 的 AlephZero 同步层），2026-10-06 本机实测。

## 1. 可复现症状与稳定错误签名

- 运行期 stderr 反复刷（`[38]` = errno 38 = ENOSYS）：
  - `fail condition broadcast[38]`（`src/libipc/platform/linux/condition.h:57`）
  - `fail condition wait[38]`（`condition.h:26`）
  - `fail mutex unlock[1]`（`linux/mutex.h:89`，`a0_mtx_unlock` 的**用户态** owner 校验 `ftx_tid(val) != tid` 返回 EPERM，
    是上游通知链断裂后锁状态不一致的**次生**现象，不是内核返回）
- gtest 上游套件逐例结果（27 例注册用例）：**13 过 / 6 失败 / 4 崩溃 / 4 超时**（13+6+4+4=27；
  逐例明细 `~/tmp/uc2/cpp-ipc-1.3.0/each-test.log`，第二次独立跑同读数）：
  - **超时 4 例**：`Queue.prod_cons_1v1_broadcast`、`Queue.prod_cons_1vN_broadcast`、
    `Queue.prod_cons_NvN_unicast`、`Queue.prod_cons_NvN_broadcast`
  - **崩溃 4 例**：`IPC.1vN`、`Sync.Condition`、`Sync.ConditionRobust`、`Waiter.broadcast`
  - **断言失败 6 例**：`IPC.basic_smb`、`IPC.1v1`、`IPC.Nv1`、`IPC.NvN`、`Sync.Mutex`、`Waiter.quit_waiting`
  - **过 13 例**：`SHM.*` 5/5；`Queue` 5/9（`check_size`、`el_connection`、`connection`、
    `prod_cons_1v1_unicast`、`prod_cons_1vN_unicast`）；`IPC.basic_ssu`、`IPC.basic_mmb`；`Sync.Semaphore`
  - **归因分寸**：崩溃与多数失败用例的 stderr 带 `fail condition broadcast[38]` / `fail condition wait[38]`，与本条机制吻合；
    但**超时 4 例（无断言输出）与 `Sync.Mutex` 的直接因果未逐例取证**（`Queue.prod_cons_NvN_unicast` 是 multi×multi 单播、
    循环 ThreadMax 轮，不排除纯负载因素）⇒ **不写"全部失败都由广播造成"，也不写"单播路径全绿"**。

## 2. 根因与最小复现

上游 a0 层的三个调用点：

```c
// src/libipc/platform/linux/a0/ftx.h
a0_ftx_cmp_requeue_pi(...)  -> syscall(SYS_futex, ..., FUTEX_CMP_REQUEUE_PI, ...)     // a0_cnd_wake 用
a0_ftx_wait_requeue_pi(...) -> syscall(SYS_futex, ..., FUTEX_WAIT_REQUEUE_PI, ...)    // a0_cnd_timedwait_impl 用
a0_ftx_trylock_pi(...)      -> syscall(SYS_futex, ..., FUTEX_TRYLOCK_PI, ...)         // owner-died 恢复分支用
```

**最小复现（30 行探针，不含任何三方库代码）**：

```c
#define _GNU_SOURCE
#include <stdio.h>
#include <errno.h>
#include <string.h>
#include <unistd.h>
#include <sys/syscall.h>
#include <linux/futex.h>

static void go(const char *name, int op) {
    int v = 0;
    errno = 0;
    long r = syscall(SYS_futex, &v, op, 1, 0, NULL, 0);
    printf("%-24s ret=%ld errno=%d(%s)\n", name, r, errno, strerror(errno));
}

int main(void) {
    printf("SYS_futex=%d\n", (int)SYS_futex);
    go("FUTEX_WAKE", FUTEX_WAKE);
    go("FUTEX_CMP_REQUEUE_PI", FUTEX_CMP_REQUEUE_PI);
    go("FUTEX_WAIT_REQUEUE_PI", FUTEX_WAIT_REQUEUE_PI);
    go("FUTEX_TRYLOCK_PI", FUTEX_TRYLOCK_PI);
    return 0;
}
```

**本机实测表（OHOS aarch64，`SYS_futex = 98`，2026-10-06）**：

| 操作 | 返回 | errno | 结论 |
|---|---|---|---|
| `FUTEX_WAKE` | 0 | — | ✅ 可用 |
| `FUTEX_WAIT`（值不匹配） | -1 | 11 EAGAIN | ✅ 可用（语义正确） |
| `FUTEX_REQUEUE` / `FUTEX_CMP_REQUEUE` / `FUTEX_WAKE_BITSET` | -1 | 22 EINVAL | ✅ 实现存在（本次入参不合法） |
| `FUTEX_WAKE_OP` | -1 | 14 EFAULT | ✅ 实现存在 |
| `FUTEX_LOCK_PI` / `FUTEX_UNLOCK_PI` | 0 | — | ✅ 可用 |
| **`FUTEX_CMP_REQUEUE_PI`** | **-1** | **38 ENOSYS** | ❌ 未实现 |
| **`FUTEX_WAIT_REQUEUE_PI`** | **-1** | **38 ENOSYS** | ❌ 未实现 |
| **`FUTEX_TRYLOCK_PI`** | **-1** | **38 ENOSYS** | ❌ 未实现 |

对照组（同一台机同一份探针）：`shm_open`/`/dev/shm` 读写/`memfd_create`/`eventfd`/`mmap`/`sem_open` 全部 OK；
`shmget` 被 seccomp 以 **SIGSYS(31) 杀进程**（rc=159）、`mq_open` **符号不存在**（musl 不提供 POSIX 消息队列）——
**三种失败形态各不相同，判据必须分开测**：`SIGSYS`（杀）/ `ENOSYS`（返回错误）/ `符号缺失`（链接期）。

## 3. 已尝试与失败的方案

- **把 `fail condition broadcast[38]` 当"上游 bug"去改上游逻辑**：不成立，根因在内核缺操作，改不动上游。
- **当测试脚本问题跳过用例**：会把平台能力缺口隐藏掉，违反"平台限制要按被禁的具体操作描述"的口径。
- **直接吞掉 ENOSYS 继续跑**：已列为 `forbid_1` —— 等待者永远等不到唤醒，退化为无界挂死。

## 4. 最终方案（本包）与真实验证

本包**没有**改并发语义（改 a0 的 wait/wake 配对降级会改变优先级继承与唤醒时机，风险与收益不成比例），而是：

1. 用探针把可用性表钉死（上表），把机制沉淀为本条知识；
2. 在 `notes.md` 与 PR 里**如实登记为平台限制**，逐条归因上游 27 例的失败；
3. 消费者测试（`test_package/test.cpp`）覆盖**确实可用**的三条路径：POSIX 共享内存句柄创建/映射/读写/释放、
   命名互斥锁开关锁、广播通道 connect/send/recv —— `conan create` 内 `1/1 Test #1: test_cpp_ipc Passed`。

**验证命令**：`clang futex_probe.c -o futex_probe && ./futex_probe`（打上表）；
上游套件：`cmake -DLIBIPC_BUILD_TESTS=ON -DCMAKE_POLICY_VERSION_MINIMUM=3.5 .. && make && ./bin/test-ipc --gtest_filter=<suite>.*`。

## 5. 适用范围 / 反例 / 解除条件

- **适用**：源码里 grep 到 `FUTEX_*_REQUEUE_PI` / `FUTEX_TRYLOCK_PI`（或 a0/`alephzero` 同步层）的库；
  自研「共享内存 + 条件变量」跨进程通知的高性能 IPC、日志、队列库。
- **反例（不受影响）**：**不经过 a0 条件变量唤醒路径**的实现 —— ①只用 POSIX 共享内存的实现（本包证据 `SHM.*`
  **5/5 全过**，只走 `shm_open`+`mmap`、不碰 cond）；②用 `pthread_cond`/`pthread_mutex` 的实现（musl 封装内部只走
  基础 `FUTEX_WAIT`/`FUTEX_WAKE`，本机探针实测可用）；③纯进程内同步。
  ⚠ **不能拿 `Queue.*_unicast` 当反例证据**：本包 `Queue.prod_cons_NvN_unicast` 同样 25s 超时、直接因果未取证
  （初稿曾写「单播路径全绿即证」，属证据不成立，已撤回）。
- **解除条件**：内核补上这三个操作后本条自动失效（探针 errno 不再是 38 即可判定）。

## 6. 查重与新增价值（四范围查重，2026-10-06）

| 范围 | 结果 |
|---|---|
| `经验文档/适配经验汇总.md` | `grep -ci futex` = **0 行 / 0 文件** |
| `knowledge/graph/index.tsv` | `futex` **0 行**；机制级 `grep -cE 'REQUEUE_PI\|TRYLOCK_PI'` = **0**；最接近的 `E051` 是 seccomp 对 `setreuid/chroot/clock_settime` 等**直接 SIGSYS 杀进程**，签名、形态、解法都不同 |
| `经验文档/经验库/` | **1 行 / 1 文件**：仅 `12b §12.21` 一句「`futex()` 直接系统调用号不同（用 pthread 封装）」——**与实测相反**：本机 `SYS_futex=98` 就是标准号，缺的是**三个操作**而非编号；本条对该粗说法构成更正 |
| `经验文档/B草稿库/` | **机制级 0 命中**（`grep -rE 'REQUEUE_PI\|TRYLOCK_PI' 经验文档/` = 0 行）；同名 `futex` 实为 **19 行 / 4 文件**（`DRAFT-PKG-VER-gnulib-gettext-futex-deadlock-gtk-option-group.{kv,md}`、`DRAFT-PKG-VER-non-ascii-build-path-breaks-locale-decoded-load-paths.{kv,md}`），机制是 **gettext 死锁**与**非 ASCII locale 挂死**，**签名与解法均不同** ⇒ 不构成重复（初稿写「0 命中」按文件口径不准确，已按实测改为机制级口径） |

⇒ **`create`**。新增价值：①把「futex 不可用」精确到**操作级**并给出完整可用性表（含对照组三种失败形态的区分）；
②给出**降级配对方案**（唤醒侧 `FUTEX_WAKE` + 等待侧 `FUTEX_WAIT`+重抢锁）与**禁止方案**（吞错误=无界挂死）；
③更正库里"系统调用号不同"的粗说法，避免后人按错方向查。
