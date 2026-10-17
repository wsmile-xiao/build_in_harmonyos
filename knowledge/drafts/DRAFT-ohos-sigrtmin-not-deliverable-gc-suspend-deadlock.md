# DRAFT-ohos-sigrtmin-not-deliverable-gc-suspend-deadlock — OHOS 不投递 `SIGRTMIN`，而 druntime 的 GC 恰好用它

> **Contributor**: ohpcd | **Status**: DRAFT | **Updated**: 2026-09-14
> **Severity**: 🔴 high (blocking) | **Category**: runtime / libc / signal / threading

## 症状

多线程的 D 程序（以及 druntime 的 unittest）在 OHOS 上**挂死**：

* 无崩溃、无输出、CPU 占用低
* 60 秒超时（不是"慢"，是彻底不动）
* 受影响的模块全部集中在**线程/GC 层面**：

```
core.thread.osthread     60s 无输出
core.thread.fiber.base   60s 无输出
core.internal.elf.dl     60s 无输出
```

⚠️ 注意失败模式是**挂死**而非崩溃——这很容易被误判为"测试环境慢"而放过。

## ★ 判别特征：只有 **35 号**这一个信号不可达

先排除"OHOS 不支持实时信号"这个直觉（**它是错的**）：

| 信号 | 编号 | `sigaction` | 处理函数是否触发 |
|------|------|-------------|-----------------|
| — | 32 / 33 / 34 | ❌ 返回 **EINVAL(22)** | — |
| **`SIGRTMIN`** | **35** | ✅ 成功 | ❌ **不触发** |
| `SIGRTMIN+1` | 36 | ✅ | ✅ |
| — | 37 – 40 | ✅ | ✅ |
| `SIGUSR1` | 10 | ✅ | ✅ |
| `SIGUSR2` | 12 | ✅ | ✅ |

**关键**：不是"实时信号不可用"（36 与 37..40 都好用），而是 **35 这一个编号**
不可达。它比 32..34 更隐蔽：

* 32..34：`sigaction` 就报 EINVAL，一眼可见
* **35：`sigaction` 成功、`pthread_kill` 返回 0（看似成功），唯独处理函数不执行**

自投递与**跨线程投递**结果一致（后者才是 druntime 的真实用法）。

## 根因：druntime 的 GC 用 SIGRTMIN 做线程挂起

```d
// runtime/druntime/src/core/thread/osthread.d:2564
suspendSignalNumber = SIGRTMIN;        // ← 35，不可达
resumeSignalNumber  = SIGRTMIN + 1;    // ← 36，可达
```

`thread_suspendAll()` 通过 `pthread_kill(目标线程, suspendSignalNumber)`
把其它线程停住，供 `thread_scanAll` 做 GC 扫描：

```
thread_suspendAll()
    → pthread_kill(t, SIGRTMIN)   ← 信号发出，但目标线程的处理函数不执行
    → 等待所有线程停稳（永远等不到）
    → 永久阻塞 → 运行时死锁
```

单线程程序不受影响（无需挂起其它线程），所以 `ldc2 --version`、简单 hello world
**都正常**——缺陷只在真正多线程 / 触发 GC stop-the-world 时暴露。

## 修复：改用 `SIGUSR1` / `SIGUSR2`

上游 LDC **已经为 OpenBSD 写过完全同构的分支**（`osthread.d:2551-2555`）：

```d
version (OpenBSD)
{
    // OpenBSD does not support SIGRTMIN or SIGRTMAX
    // Use SIGUSR1 for SIGRTMIN, SIGUSR2 for SIGRTMIN + 1
    enum SIGRTMIN = SIGUSR1;
    enum SIGRTMAX = 32;
}
```

OHOS 沿用同一思路：

```d
if ( suspendSignalNumber == 0 )
    suspendSignalNumber = SIGUSR1;      // 原 SIGRTMIN
if ( resumeSignalNumber == 0 )
    resumeSignalNumber = SIGUSR2;       // 原 SIGRTMIN + 1
```

### 效果（唯一变量即此改动）

| | PASS | FAIL | TIMEOUT | 通过率 |
|---|---|---|---|---|
| 未打补丁 | 50 | 7 | **3** | 50/60 = 83.3% |
| **打补丁后** | **52** | 2 | **1** | 52/55 = **94.5%** |

原 3 个超时模块中 **2 个转为 PASS**：

```
core.thread.osthread     60s 卡死 → rc=0  0.113s  ✅ PASS
core.thread.fiber.base   60s 卡死 → rc=0  0.014s  ✅ PASS
core.internal.elf.dl     仍超时（另因，未定性）
```

> **排除统计噪声**：未打补丁 / 打补丁的两个 runner 二进制 sha256 **各不相同**，
> 且该改动是二者之间的唯一差异。

## 最小复现（不依赖 D）

```c
#include <stdio.h>
#include <pthread.h>
#include <signal.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>

static volatile sig_atomic_t got = 0;
static void h(int s){ (void)s; got++; }

int main(void){
    for (int sig = 32; sig <= 40; sig++) {
        got = 0;
        struct sigaction sa; memset(&sa, 0, sizeof sa);
        sa.sa_handler = h; sa.sa_flags = SA_RESTART; sigfillset(&sa.sa_mask);
        if (sigaction(sig, &sa, NULL) != 0) {
            printf("sig=%-3d sigaction EINVAL(%d)\n", sig, errno);
            continue;
        }
        pthread_kill(pthread_self(), sig);
        usleep(150000);
        printf("sig=%-3d fired=%d %s\n", sig, got, got ? "OK" : "<-- 不可达");
    }
    return 0;
}
```

OHOS 实测输出（关键行）：

```
sig=32  sigaction EINVAL(22)
sig=33  sigaction EINVAL(22)
sig=34  sigaction EINVAL(22)
sig=35  fired=0 <-- 不可达          ← SIGRTMIN
sig=36  fired=1 OK                  ← SIGRTMIN+1
sig=37  fired=1 OK
...
```

## 适用范围

任何「用 `SIGRTMIN`/`SIGRTMIN+1` 做线程间停/启同步」的运行时或库，在 OHOS 上都会死锁：

* 语言运行时的 GC（D 的 druntime 是最直接的一例）
* 采样 profiler（信号驱动栈采样）
* 线程暂停器 / stop-the-world 机制
* 信号驱动的 checkpoint / 快照

**排查提示**：若见到"多线程挂死、无输出、低 CPU"，且代码里有 `SIGRTMIN`，
基本可断定是此问题。判别顺序：

1. 先确认处理函数是否真被调用（上节最小复现）
2. 再确认用的是不是 35 号（`grep -rn SIGRTMIN <源码>`）

## 禁止的两种做法

**❌ 把超时的多线程测试标记 skip / 忽略**

这不是测试问题，是运行时缺陷——任何用到 GC 的多线程程序都会死锁。
跳过测试只是掩盖；而且失败模式是"挂死"，极易被误判为"环境慢"而放过。

**❌ 认为"OHOS 不支持实时信号"而放弃实时信号的一切用法**

实测 `SIGRTMIN+1`(36) 与 37..40 **都正常**，只有 35 一个不可达，属**特例**。
据此否定实时信号是**做过头**，可能否决本可实现的方案。更稳的替代是
37..40 中未被占用的编号。

## 诚实标注（limitations）

1. **"35 号不可达"是实测现象**，我**没有拿到内核侧的解释**（为何恰好是 35）。
   结论以行为为准：`sigaction` 成功、`pthread_kill` 返回 0、处理函数不执行。
2. **修法用 `SIGUSR1`/`SIGUSR2` 有冲突风险**：这两个是通用用途信号，目标进程内的
   其它组件（OpenSSL 等）可能已占用，落地时须评估。
3. **未验证 Android / 其它 musl 平台是否同样如此** —— 不能假定这是"musl 通病"。
4. `core.internal.elf.dl` 打补丁后**仍超时**，它另有原因，本条未定性。

## 相关

| 条目 | 关系 |
|------|------|
| `DRAFT-libkqueue-2.6.1-ohos-sigwaitinfo-si-fd-monitor` | **现象不同、机制不同**。那条讲 `sigwaitinfo` 的 `si_fd` 恒为 0，以及 `F_SETSIG` 触发的 close 通知**偶发**不投递；本条是 **35 号编号确定性不可达**。不过本条的发现（35 号是特殊编号）**恰好能解释**那条观察到的"RT 信号偶发不投递"——若其用的是 `SIGRTMIN`，那些"偶发"失败可归因于此 |
| 32..34 的 `sigaction` EINVAL | 同一排查过程中的附带证据：32..34 被内核占用但不可用；35 更隐蔽（API 全部成功、只有投递无效）|
