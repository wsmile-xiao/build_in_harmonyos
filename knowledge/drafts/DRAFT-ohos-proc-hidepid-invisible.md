# DRAFT — OHOS 的 /proc 以 hidepid=invisible 挂载：读其它进程 /proc/<pid>/* 一律被拒，进程树类 API 需优雅降级

> 触发事件：psutil 7.2.2 HarmonyOS PC 适配（PR #11263，2026-09-19 真机实测）
> 主从明确：**E031**（/proc SELinux 访问限制）为根条目；本条补充其**实际挂载机制**
> （`hidepid=invisible` 而非单纯 SELinux 策略）、**可读边界**（仅 `self` 可读）与
> **对进程树枚举类 API 的后果**，并记录 E031 推荐方案（sudo-run）在 CI/conan 环境不可用。

## 现象

psutil 上游套件中所有需要**遍历/读取其它进程**的用例成片失败（实测 158 项失败里
46 处命中同一位置 `psutil/_pslinux.py:1575` 的 `ppid_map()`）：

```text
psutil.AccessDenied: (pid=1)
  File ".../psutil/_pslinux.py", line 1575, in ppid_map
    raise AccessDenied(pid) from err
```

## 根因（实测）

`/proc` 的挂载参数直接写明拒绝策略：

```text
$ grep ' /proc ' /proc/mounts
procfs /proc procfs rw,relatime,hmmac=genfs,gid=3009,hidepid=invisible 0 0
```

**可读边界（逐项实测）**：

| 目标 | 结果 |
|---|---|
| `/proc/self/stat`、`/proc/self/status`、`/proc/self/cmdline` | ✅ 可读 |
| `/proc/1/stat`、`/proc/1/status`、`/proc/1/cmdline` | ❌ `PermissionError` |
| 任意其它 pid 的 `/proc/<pid>/stat` | ❌ `PermissionError`（对可见 pid 列表逐个抽样，全部 DENIED） |

**关键反直觉点**：进程 uid `20020085` 的补充组里**已包含 `3009(readproc)`**（即
`/proc` 挂载的 `gid=3009`），但**仍被拒**——说明 `hidepid=invisible` 的判定不因
补齐 readproc 组而放开。排查时**不要**据此认为"加了组就能读"。

## 适用面

所有依赖**跨进程 /proc 信息**的库与工具：

- 进程树类 API：`children()` / `parents()` / `ppid()` / `pstree` / 孤儿进程回收
- 系统级进程枚举后的逐 pid 属性读取（`Process(pid).name()/cmdline()/status()`）
- 先例同类：`libgtop` 2.41.3（notes.md 已记录"OHOS 普通用户无法读 /proc/1/stat 等
  系统进程，专项测试用 getpid() 自身进程验证"）

> 注意与 `/proc/stat`、`/proc/meminfo` 的区别：这两者**普通用户可读**（E031 的
> `error_signature` 覆盖的是它们）；本条的拒绝面是 **`/proc/<pid>/*` 逐进程文件**，
> 两者是同族但**不同文件**的受限面。

## 推荐方案

**代码级优雅降级（capability probe）**，不要 die：

1. 以 `PermissionError` / `AccessDenied` 为**能力探测信号**：跨进程读取失败时，
   将进程树维度标记为"本平台不可用"，返回空集或 `None`，并保持其余 API 可用；
2. 面向消费者文档写明"OHOS 上跨进程信息不可用"，而不是让调用方拿到异常崩溃；
3. 测试侧改为**只验证自身进程**（`getpid()`），跨进程用例如实归因（列入允许失败
   清单并给出本条根因）。

## 禁止做法

```text
rec_approach: sudo-run          # ← E031 的推荐方案，在本环境不可用
```

- ❌ **不要用 `sudo-run` 规避**：CI / conan 包构建环境**没有 sudo**，该方案在 CI
  必然失败（E429 的 `causes` 已记录同一结论："E031 的 sudo-run 方案在 CI 不可用"）。
- ❌ 不要尝试"加 readproc 组"：实测 uid 已在 `3009(readproc)` 组内仍被拒。
- ❌ 不要为绕过权限而改 `/proc` 挂载参数：由系统镜像决定，配方/应用层无法变更。

## 验证证据

```sh
# ① 挂载参数（根因直读）
grep ' /proc ' /proc/mounts          # → ...,gid=3009,hidepid=invisible
# ② 可读边界
head -c 40 /proc/self/stat           # 正常
head -c 40 /proc/1/stat              # Permission denied
# ③ 组身份对照（证明加组无效）
id                                   # groups 含 3009(readproc)
head -c 40 /proc/1/status            # 仍 Permission denied
```

- **主证据**：psutil 7.2.2（PR #11263）实测 —— 158 failed 中 46 处命中
  `_pslinux.py:1575 ppid_map()` 的 `AccessDenied`，根因即本条。
- **交叉佐证**：libgtop 2.41.3 适配（`archives/l/libgtop/2.41.3/notes.md`）记录
  同一受限面，专项测试改用 `getpid()` 自身进程验证。
- **环境**：HarmonyOS PC / aarch64 / 内核串 `HongMeng Kernel 1.12.0`。

## 查重结论

- 全库对 `hidepid` 命中仅 2 处：`knowledge/operations/filesystem-analysis.md:296`
  的迁移留痕（`<!-- ~~### 10.6 procfs hidepid=invisible~~ → 已迁移至 graph/E031.kv
  + doc/E031.md -->`）与 **E031** 本身。E031 的 `root_cause` 只写"SELinux 策略限制"
  ，**未记录 `hidepid=invisible` 这一实际挂载参数**、未给出"仅 self 可读"的边界、
  未涉及进程树枚举后果，且其推荐方案 `sudo-run` 在 CI 不可用（E429 已证）——本条
  为差异化补充，**E031 仍为根条目**。
- 对 `ppid_map`、`AccessDenied`、`readproc` 检索：无其它条目覆盖。
- 盲区声明：以上基于本地已合并知识（本地 main + 本分支），无法保证外部无人提交过
  同主题草稿。
