# OHOS fork 跨进程共享 signalfd 虚假可读（EAGAIN）→ 事件循环误分发信号回调

- **草稿**: DRAFT-libuev-2.4.1-ohos-fork-signalfd-eagain-spurious
- **来源**: libuev 2.4.1 第一轮适配（OHOS PC arm64，`make check` 阶段）
- **状态**: 草稿（随 libuev 归档 PR 提交，待审核 promote）
- **适用边界**: 仅 OHOS/HarmonyOS（Linux 兼容内核）上的 signalfd + epoll
  事件循环库/守护进程；真实 Linux 上不出现或极罕见，勿跨平台误用

## 问题

libuev 2.4.1 上游测试 `test/signal.c` 在 OHOS 上确定性失败（5/5）：

```
child[35225] magic 1337 ptr 0, event 6137 event arg 0
Child 35225 crashed, as expected, everything is OK.
signal: PID 35214 caused segfault.        ← 父进程误判自己 SIGSEGV
FAIL signal (exit status: 255)
```

父进程注册 SIGSEGV + SIGCHLD 两个 signal watcher 后 `fork()` 子进程，子进程
故意崩溃（SIGSEGV）。子进程死亡后，父进程的 SIGSEGV signalfd 被 epoll 报告
可读，但 `read()` 返回 `-1 errno=EAGAIN`（无真实信号数据），libuev 原实现
仍以 UEV_READ 分发回调（siginfo 置零），回调按 `w->signo=SIGSEGV` 误判父进程
崩溃并 `exit(-1)`。

## 根因

OHOS（HongMeng Kernel 1.12）上 `signalfd(2)` 的 fd 经 `fork(2)` 后父子进程
共享同一 open file description。子进程持有的、被 `sigprocmask` 屏蔽且被
signalfd 监视的信号（如崩溃产生的 SIGSEGV），会反映到共享 signalfd 上使父进程
`epoll_wait` 报告可读；但该信号不属于父进程（或已随子进程死亡回收），父进程
`read()` 时无数据 → EAGAIN。事件循环库把 "read 失败" 一律当作真实信号事件
分发，即产生误判。

## 方案

事件循环分发路径中，对 signalfd 的 `read()` 失败区分：

| 情况 | errno | 处理 |
|---|---|---|
| 虚假可读（fork 共享 fd 残留可读） | EAGAIN / EWOULDBLOCK | `continue` 跳过回调，保持 watcher 活跃，不重启不停止 |
| 其它真实错误 | 其它 | 按原逻辑重启 watcher 或上报 UEV_ERROR |

libuev 最小补丁（`patches/0001-src-uev.c.patch`，无平台宏，R8 合规）：

```c
case UEV_SIGNAL_TYPE:
    if (read(w->fd, &fdsi, sz) != sz) {
        if (EAGAIN == errno || EWOULDBLOCK == errno) {
            /* Spurious wakeup: signalfd shared across fork(), signal was
             * generated for a child process, not for us.  Skip callback. */
            continue;
        }
        if (uev_signal_start(w)) { ... }
        memset(&w->siginfo, 0, sizeof(w->siginfo));
    } else
        w->siginfo = fdsi;
    break;
```

## 验证

- 补丁前: `make check` → 6/7，signal FAIL（exit 255），5/5 确定性
- 补丁后: `make check` → 7/7 PASS（test/test-suite.log）
- 专项测试 `tests/ohos_platform_test.c`（随 PR 交付）复现同一 fork 场景，
  断言父进程只收到 SIGCHLD（`got_sigchld==1`），PASS (exit 0)
- 修复仅新增 EAGAIN 守卫分支，不影响正常信号路径（6/7 原本通过的测试
  补丁后仍全过）

## 适用边界与反例

- **适用**: 任何使用 signalfd 监视被 fork 子进程可能持有的信号的事件循环
  库（libuev/libev/libevent 等 signalfd 集成路径）、进程看护/插件隔离/
  测试桩等 fork + 子进程崩溃/退出的 OHOS 应用
- **反例/不适用**: 真实 Linux（无此内核行为差异，上游 CI 通过即证明）；
  不使用 signalfd（如 sigaction + self-pipe）的库；不 fork 的应用
- **不要做**: 不要用 `#ifdef __OHOS__` 平台宏硬编码跳过该测试（R8）；
  不要修改上游测试掩盖问题——正确做法是修库内 read 失败处理

## 与既有知识关系

- `similar_to` E399（epoll-shim ctest 排除 signalfd blocking 测试——词面
  重叠但根因是 kqueue 语义差异，方案是 ctest 排除，与本模式根因/方案不同）
- `similar_to` DRAFT-libkqueue-2.6.1-ohos-sigwaitinfo-si-fd-monitor（RT
  信号 sigwaitinfo/si_fd 语义，非 signalfd/共享 fd，方案不同）
- 无 conflicts_with / caused_by / prerequisite_of

## 查重结论（七轴）

| 轴 | 结论 |
|---|---|
| exact_duplicate | false |
| causal_duplicate | false |
| trigger_overlap | partial（与 E399 仅 "signalfd" 词面重叠，触发机制不同） |
| solution_overlap | false（E399 为 ctest 排除，本模式为库内 read 守卫） |
| combination_novelty | true |
| boundary_novelty | true（事件循环库 fork 场景、守护进程场景） |
| test_migration_novelty | true（ohos_platform_test 复现路径可迁移其他事件循环库） |

**决定: new_draft（路径 B 知识库扩展）** — 已验证、可跨库复用、四范围查重
未命中且有新增差异，随 libuev 归档同 PR 提交。
