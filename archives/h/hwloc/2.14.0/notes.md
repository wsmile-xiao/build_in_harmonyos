# hwloc 2.14.0 编译笔记（HarmonyOS PC · 标准 Conan autotools）

## 定位
- 产出 libhwloc.so 等 1 个库，供链接与 dlopen。

## 关键适配
- 删除 lib/*.la：其中烤死 libdir 绝对路径，会把下游 libtool 引到 //lib/ 死路
- 修 configure 的 umask 077→022（HMDFS E011）

## 补丁说明

### 0001-ohos-numa-membind-enosys.patch —— NUMA 内存 syscall 被 seccomp 拦截

**问题.** 设备实测（faultlog）：

```
Reason:Signal:SIGSYS(SYS_SECCOMP) syscall number is 236
```

aarch64 上 236 = `get_mempolicy`。该 seccomp 策略**直接杀进程**，不是返回 ENOSYS ——
独立探针证实：`syscall(236, ...)` → `Bad system call (core dumped)`，退出码 159。

而 musl 已定义 `__NR_get_mempolicy=236`，于是 hwloc 的
`#if (defined __NR_get_mempolicy) && (defined HWLOC_HAVE_SYSCALL)` 判真，把 syscall 编了进去。

**后果.** `lstopo` / `lstopo-no-graphics` **每次必崩**（`lstopo.c:1891` 无条件调
`hwloc_get_membind`，无 CLI 开关可跳过）。oneTBB 等在 NUMA 场景调 `hwloc_set_membind`
的消费方同样被打死。

**修法.** 给 5 个 NUMA 内存 syscall 的守卫加 `!defined(HWLOC_MEMPOLICY_SYSCALL_UNUSABLE)`，
走**上游本来就有的** `errno = ENOSYS; return -1;` 分支——那正是「本平台不支持内存绑定」
的标准语义，hwloc 各调用方都能优雅处理（`hwloc-info` / `hwloc-calc` 不调 membind，故一直正常）。

**该宏不是平台宏，而是由构建期行为探针决定的能力宏。**
配方在 `generate()` 里编译并运行一段调用 `get_mempolicy` 的探针：

- 探针被 SIGSYS 打死 → 定义该宏 → 走 ENOSYS 分支
- 探针正常返回 → 不定义 → 保留上游原生实现

因此平台将来放开该 syscall 时，功能会**自动恢复**，无需改补丁；
其他平台上探针通过，本补丁完全无影响。

**为什么必须「运行」探测而非编译期判断.** seccomp 是 KILL 语义，编译期看不出来，
进程内也无从恢复（捕获 SIGSYS 无用）。

**否决的方案及理由.**

| 方案 | 否决理由 |
|---|---|
| 捕获 SIGSYS | KILL 语义，进程内无从恢复 |
| `--disable-*` 关掉 | hwloc 没有对应 configure 开关（已核 `configure.ac`） |
| 只修 `get_mempolicy` | 只修一个，`set_mempolicy` / `mbind` 路径照样崩 |

## 状态
built（真机 conan create + test_package 通过）
