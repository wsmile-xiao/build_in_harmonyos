# DRAFT-librtpi-100 — HongMeng 内核未实现 PI 重排队 futex（condvar ENOSYS）

- 日期：2026-09-19
- 软件：librtpi 1.0.0（真机单包实测）
- 设备：HarmonyOS PC（LAN 10.62.178.77），HongMeng Kernel 1.12.0，aarch64
- 配套条目：`DRAFT-librtpi-100-hongmeng-futex-requeue-enosys.kv`

## 现象

librtpi test_package 第 3 阶段（无信号者 `pi_cond_timedwait` 能力探针）返回
errno 38（ENOSYS）：

```
FAIL: pi_cond_timedwait returned 38 (Function not implemented)
```

同一次运行中第 2 阶段（双线程竞争 `pi_mutex_lock`，走
`FUTEX_LOCK_PI`/`FUTEX_UNLOCK_PI` 慢路径）**通过**。

## 根因

librtpi 不使用 libc 的 pthread PI mutex，而是直接调用 Linux PI futex
系统调用自行实现优先级继承：

| 系统调用 | 用途 | HongMeng 1.12.0 实测 |
|---|---|---|
| `FUTEX_LOCK_PI` / `FUTEX_UNLOCK_PI` | PI 互斥锁 | ✅ 已实现（阶段 2 通过） |
| `FUTEX_WAIT_REQUEUE_PI` | condvar 等待并重排队到 PI 锁 | ❌ ENOSYS |
| `FUTEX_CMP_REQUEUE_PI` | condvar 唤醒/重排队 | ❌ 未测到（等待先失败） |

glibc/musl 的 pthread PI mutex 只依赖 LOCK_PI/UNLOCK_PI，所以普通库不受
影响；librtpi 的 condvar 必须用重排队族，因此其条件变量 API 在该内核上
运行期不可用。`/proc/config.gz`、`/proc/kallsyms` 在真机不可读，只能
运行期探针判定。

## 处理建议

1. **交付语义**：ENOSYS 是平台能力事实，不是包缺陷——test_package 将其
   作为探测结果报告（`condvar: UNSUPPORTED` 标记，mutex API 照常硬断言），
   其余 errno 仍硬失败；PR/notes.md 如实记录。
2. **排查顺序**：ENOSYS=内核未实现；EINVAL=标志组合不支持；EAGAIN/EPERM
   走库内唤醒竞态协议，不属内核缺口。
3. **需要完整 PI condvar 的用户**：向内核团队申请补齐重排队支持；或接受
   mutex-only 使用面。
4. **新真机验证 PI-futex 类库时先跑探针**，不同批次真机内核实现可能不同。

## 关联知识

- E127（OHOS musl 无 pthread_cancel 族）——同类"平台能力缺口"模式，
  处理方式一致：用上游原生开关/探测语义绕开并如实记录。
- E524（共享前缀污染）——本轮实测期间真机 `$HOME/usr/local/bin/cmake`
  被并行任务删除，属同一风险面，已用 `/data/service/hnp/bin` + runner
  `--path` 绕开。
