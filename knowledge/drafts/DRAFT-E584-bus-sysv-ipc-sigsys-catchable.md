# DRAFT-E584：OHOS 沙箱对 System V IPC 触发 SIGSYS（可捕获）——SysV IPC 为公开 API 的库的适配验证与平台限制通告

> Contributor: bus 3.1.11 适配任务（pc2-21） | Status: Draft | Updated: 2026-09-19
> Source: 任务卡 `bus` 3.1.11（开源鸿蒙 PC 专项积分赛知识库扩展，分支 `feat/bus-3.1.11`）
> 与 DRAFT-E577（buffer 1.19，SysV IPC → POSIX 迁移）同根因、不同解：E577 面向可改写
> 程序，本条目面向"IPC 即公开 API、无 POSIX 等价分支"的不可改写库。

## 背景

`bus` 3.1.11（Mattias Andrée）是一个无守护进程的本地消息广播系统：C 库 libbus 的公开
API（`bus_create`/`bus_open`/`bus_write`/`bus_read`/`bus_poll_*`…）全部建立在 System V
信号量（`semget`/`semop`/`semctl`）与 System V 共享内存（`shmget`/`shmat`…）之上，另有
命令行工具 `bus`（create/remove/listen/wait/broadcast/chmod/chown/chgrp）。

在 OHOS 设备（HongMeng Kernel 1.12.0 aarch64，AppSpawn 沙箱）上，任何调用
`semget`/`shmget` 的程序直接死亡：

```text
$ ./bus create /tmp/x
Signal 31 (core dumped)          # SIGSYS，无任何 errno/权限提示

$ ./semprobe                     # 10 行最小复现：semget + shmget
Signal 31 (core dumped)          # exit 159
```

## 关键新证据（相对 E051/E246/E577 的差异）

1. **该 SIGSYS 可捕获**：`sigaction(SIGSYS, handler)` + `sigsetjmp/siglongjmp`
   可捕获并继续执行（seccomp TRAP 语义）。这与 E051 记载的"未实现 syscall
   （setreuid/setregid）SIGSYS 不可捕获、进程直接终止"相反——E051 是内核未实现，
   本场景是 seccomp 拦截，语义不同，处理方式也不同。

   ```text
   $ ./sigtest
   SIGSYS CAUGHT -> semget blocked by sandbox, errno=0
   ```

2. **POSIX IPC 面不受阻**：`sem_open("/name", 0)` 返回 ENOENT 而非 SIGSYS；
   `shm_open`+`mmap(MAP_SHARED)`、匿名 `MAP_SHARED|MAP_ANONYMOUS` 均正常
   （与 DRAFT-E577 旁证一致）。

3. **不返回 -1/errno**：被 seccomp 拦截时进程直接被 SIGSYS 终止，按 errno 写的
   回退分支永不触发（E577 forbid_2 同口径）。

## 适配与验证方案（rec_approach: compile-link-deliver-plus-platform-limitation-disclosure）

SysV IPC 是 libbus 的公开 API 契约，无法像 buffer 那样把 IPC 层整体迁到 POSIX
（迁移=重写库语义，非补丁）。因此：

1. **编译/链接/打包交付**：零源码补丁；conan-verify 8 门禁全过（G0-G4 + L2/L4/L5）。
2. **消费者用例走非受限路径**：`bus_open` 打开不存在的文件 → 返回 -1/errno=ENOENT
   （在 fopen 处即失败，不触达 semget），证明公开头文件/链接/运行链路可用。
3. **鸿蒙专项测试安装 SIGSYS handler**：先做可运行断言（BUS_MEMORY_SIZE、
   bus_open ENOENT），再尝试真实 `bus_create` 往返；捕获 SIGSYS 即打印
   `PLATFORM_LIMITATION` 与恢复条件（非沙箱/系统服务/启用 SysV IPC 内核），
   从而区分"平台限制"与"真实缺陷"。
4. **CLI 冒烟**：`bus`（无参）→ 文档规定退出码 2（"command not recognised"），
   不触发受限 syscall，验证二进制可在 OHOS 执行。
5. **上游测试台账**：23 个示例全量枚举、23/23 编译通过；运行全部 SIGSYS
   平台阻塞，计"未运行/平台阻塞"而非通过（全量通过率口径如实填写）。

## 验证结果

| 项 | 结果 |
|---|---|
| conan-verify（G0-G4/L2/L4/L5） | ✅ PASS |
| 消费者用例（bus_open ENOENT） | ✅ exit 0 |
| 鸿蒙专项（test_ohos） | ✅ exit 0，PLATFORM_LIMITATION 如实报告 |
| CLI 冒烟（bus 无参） | ✅ exit 2（文档规定） |
| 上游示例 23/23 编译 | ✅；运行 SIGSYS 平台阻塞（台账） |
| 探针证据 | semprobe（SIGSYS）、sigtest（可捕获）、sem_open（ENOENT） |

## 适用边界

- 适用：以 System V IPC（shmget/semget/msgget 家族）为进程间通信主干、
  无 POSIX 等价分支、IPC 即公开 API 的 C 库/工具（如本包 bus、类 System V
  消息队列库）。
- 不适用/反例：①可改写程序（buffer/afl 类）→ 走 DRAFT-E577 的 POSIX 迁移；
  ②库自带 POSIX 回退分支（如 E237 acpid 类运行时降级）→ 走既有降级条目；
  ③非 IPC 的 seccomp 拦截（adjtimex）→ E246。
- 边界判定：**"IPC 层与库的公开 API 是否耦合"**——耦合则本条目，可剥离则 E577。

## 关系字段

- similar_to: [E051, E220, E246, DRAFT-E577]
- caused_by: []（无前置知识缺口）
- prerequisite_of: [] 
- conflicts_with: []（与 E577 互补：同根因、不同解，按边界划分适用）

## 验收口径（跨库可复用）

测试统计必须使用双口径台账；运行期 SIGSYS 的入口计入总分母但不计为通过，并在
"未运行/平台阻塞"列写明命令、退出码、首错与恢复条件；禁止 timeout/管道吞 SIGSYS
制造假通过（forbid_3）。