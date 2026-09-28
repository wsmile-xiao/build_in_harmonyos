# DRAFT-secpwgen-1.3-e051-privileged-id-noop-guard — 特权 id syscall 的 PF5 兼容修法

> 草稿（draft: true），待主编审核后 `graph promote` 为正式 E 条目。
> 来源任务：secpwgen 1.3 适配 HarmonyOS PC（分支 `feat/secpwgen-1.3`，2026-09-22）。

## 错误特征

```
exit code 159 | Bad system call | killed ... signal 31 | SIGSYS
FATAL: system call failed.
程序启动即退出、stdout 一行输出都没有
```

崩溃点落在 `seteuid` / `setreuid` / `setregid` / `setegid` / `setuid` / `setgid` 上。

## 触发条件

- 构建系统: 任意（问题在运行时）
- 阶段: 运行时（多数在进程启动的初始化阶段，例如 drop privileges）
- 前置条件: 进程为非特权（普通用户）身份，且代码无条件调用了特权 id syscall

## 根因分析

鸿蒙对应用/沙箱进程采用白名单式 seccomp 策略，特权 id syscall 族不在允许列表内。
非特权进程发起时，内核**直接以 SIGSYS（signal 31，退出码 128+31=159）终止进程**：

- 不返回 -1，也不设置 errno → 任何 `if (seteuid(...) < 0)` 错误分支都走不到
- 该 SIGSYS **不可被捕获** → `signal(SIGSYS, ...)` / `sigaction` 方案完全无效（E051 实测）

本仓已有 6 处独立实证：`uid-wrapper 1.2.5`、`libgtop-tools 2.41.3`、`hfsutils 3.2.6`、
`cdrkit 1.1.11`、`pwsafe 1.24.0`、`screen 5.0.0`（均见各自 notes.md）。

### 为什么这是一条"知识缺口"而不只是 E051 的重复

E051 把根因描述得很准确，但它给的修法是：

> 在 C 源码中用 `#ifdef __OHOS__` 守卫，在 syscall 调用前直接返回 errno=ENOSYS 并 return -1

这条修法**现在会被门禁拦下**：v12.17+ 的 R8 明确"patches/ 补丁文件中不应引入
`#ifdef __OHOS__`，应通过 POSIX 兼容方式修复"，`scripts/ohc/preflight.py` 的
**PF5 平台宏闸**对 patches/*.patch 新增行出现 `__OHOS__` 一律 fail-closed（PR 建不出来）。

冲突面还不止 E051：`knowledge/principles.yaml` 有三条原则仍在要求平台宏守卫，其中
`P-RUNTIME-001` 的 level 是 **critical**：

| 原则 | level | 现状表述 | 与 PF5 的关系 |
|------|-------|----------|---------------|
| P-RUNTIME-001 | critical | "必须用 `#ifdef __OHOS__` 在调用前 return ENOSYS" | 直接冲突 |
| P-PATCH-002 | high | "`#ifdef __OHOS__` 是平台隔离标准写法" | 直接冲突 |
| P-SYSCALL-001 | high | "必须在源码中用 `#ifdef __OHOS__` 守卫做兼容处理" | 直接冲突 |

`DRAFT-E577` 已经指出"E051 的旧方案已失效"，但它只给了 **SysV IPC**（shmget/semget/
msgget）的替代路线，没有覆盖特权 id syscall 这一族。本条目补的就是这一格。

## 解决方案

### 推荐方案：POSIX 空操作守卫（无平台宏）

先问一句：**这次调用在语义上是不是空操作？** 绝大多数 drop privileges 写的是
`seteuid(getuid())` / `setreuid(ruid, ruid)`，对普通（非 setuid）进程而言它按 POSIX
不改变任何 uid，纯属空转。把判定提到调用之前即可：

```c
 static void drop_privileges(void)
 {
+	/* 只在确实持有额外特权（setuid 二进制）时才需要丢弃。普通调用下这次
+	   seteuid 是空操作，而某些平台会拒绝非特权进程发起特权 id syscall，
+	   此时根本没有特权可丢，却会让启动直接失败。 */
+	if(geteuid() == getuid())
+		return;
+
 	if(seteuid(getuid()) < 0) {
 		perror("seteuid");
 		Throw(system_call_failed_exception);
 	}
 }
```

对应关系：

| 上游写法 | 守卫条件 |
|----------|----------|
| `seteuid(getuid())` | `if (geteuid() == getuid()) return;` |
| `setegid(getgid())` | `if (getegid() == getgid()) return;` |
| `setreuid(r, r)` | `if (geteuid() == getuid()) return;` |
| `setregid(g, g)` | `if (getegid() == getgid()) return;` |

优点：

- **无平台宏** → 满足 R8「修改对非鸿蒙平台必须是透明的」与 PF5
- **语义等价** → 空操作被消除，真 setuid 二进制仍走原路径、原样报错（不破坏上游逻辑）
- **改动量小** → secpwgen 实测 +11/-0、单 hunk
- **可向上游提交**（P-PATCH-003）：这是纯可移植性改进，Linux/BSD 上同样成立

### 禁止做法

- ❌ `#ifdef __OHOS__` 守卫 —— PF5 fail-closed，PR 建不出来（E051 与三条 principles 的旧建议）
- ❌ 把失败改成非致命（`if (seteuid(..)) /* ignore */;`）—— SIGSYS 在 syscall 返回前就杀进程，
      错误分支永远走不到。`screen 5.0.0` 对 seteuid 用的正是这种口径，对"返回 errno"的平台
      有效，对鸿蒙无效
- ❌ 装 SIGSYS handler —— 不可捕获，handler 从不被调用
- ❌ 按 errno 写回退逻辑 —— 内核不设 errno

### 不适用时的退路

调用**确实**需要改变 uid/gid（不是空操作）时，本方案不适用。改用运行时能力探测：
fork 子进程试调目标 syscall，父进程 `waitpid` 判 `WIFSIGNALED` / SIGSYS，据此在运行期
选择替代路径（放弃降权并告警，或改用平台允许的机制）。与 DRAFT-E577 的 fallback 同型。

## 验证

```bash
# 1) 设备复现：未打补丁的产物启动即死
./secpwgen -p 4; echo "exit=$?"        # 期望（未修复）: exit=159 或 Bad system call

# 2) 设备验证：修复后正常产出
./secpwgen -p 4; echo "exit=$?"        # 期望（已修复）: 输出通行短语 + exit=0

# 3) 无需设备：确认补丁真的编进了产物（比对目标文件的未定义符号）
llvm-nm -u <build>/secure_memory_unix.o | grep -E 'get(e)?uid|seteuid'
#   未打补丁: U getuid, U seteuid                      → 守卫缺失
#   已打补丁: U geteuid, U getuid, U seteuid           → 守卫已编入

# 4) 反证：链接产物层面不可用（静态 libcrypto 自身也引用 geteuid）
llvm-nm -u <build>/secpwgen | grep geteuid             # 打补丁前后输出相同，无区分度
```

第 3 步已在本仓固化成可执行断言：`archives/s/secpwgen/1.3/test_package/ohos_abi_check.py`
的 `A4_e051_seteuid_guard`（纯 Python 解析 ELF `.symtab`，不依赖 worker 上有没有
`readelf`/`llvm-nm`，因此在"能交叉编译但不能执行目标二进制"的 macOS 模拟环境里同样能跑）。
实测区分度：未打补丁 → A4 FAIL / rc=1；已打补丁 → A4 PASS / rc=0。

## 关联条目

- 相关: E051（同一根因；其 rec_description 的 `__OHOS__` 修法已失效）
- 相关: DRAFT-E577（SysV IPC 族同样死于 SIGSYS，但那族无法用空操作判定消除，须换 POSIX 原语）
- 相关: E246（seccomp 拦截返回错误码 vs 本条的直接杀进程，二者处置方式不同）
- 冲突: `principles.yaml` 的 P-RUNTIME-001 / P-PATCH-002 / P-SYSCALL-001 建议文本
  （建议主编同步修订，否则知识引擎会把适配者导向被 PF5 拦下的写法）
- 实例: `archives/s/secpwgen/1.3`（本条来源）、`archives/s/screen/5.0.0`（forbid_2 反例）、
  `archives/h/hfsutils/3.2.6` 与 `archives/p/pwsafe/1.24.0`（forbid_1 反例，PF5 之前合入）
