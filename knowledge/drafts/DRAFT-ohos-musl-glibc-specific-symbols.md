# DRAFT-ohos-musl-glibc-specific-symbols — musl libc 缺 glibc 特有符号时的统一处置

> Contributor: 3A2F / Status: **DRAFT** / Updated: 2026-09-16 / Severity: 2 (medium)
> Prospect ID: `DRAFT-ohos-musl-glibc-specific-symbols`（正式编号由主编 `graph promote` 分配）

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本条的增量（差异化） |
|---|---|---|---|
| `E051` | 图谱 | OHOS 内核**缺 syscall**（SIGSYS/ENOSYS，如 setreuid/chroot）| 内核系统调用层；本条是 **libc 符号层**（编译期）|
| `E086` | 图谱 | `struct ucred` / `SO_PEERCRED` / `SCM_CREDENTIALS` 缺失，`__OHOS__` 守卫 | socket 结构/常量层；本条是**函数/变量符号**层 |
| `E102` | 图谱 | `mmsghdr` / `recvmmsg` 缺失，从 `__linux__` 条件排除 OHOS | 头文件结构层；本条是 libc 符号层 |
| `E091` | 图谱 | `sockaddr_storage` 重复定义（linux/socket.h vs sys/socket.h）| 头文件冲突层；本条是符号缺失层 |

**全库查证**：对 `program_invocation_short_name` / `get_current_dir_name` /
`program_invocation_name` / `__progname` 等关键词，在 `knowledge/index.tsv`、
`knowledge/graph/index.tsv`、`knowledge/graph/*.kv`、`knowledge/doc/*.md`、
`knowledge/drafts/*.kv`、`knowledge/drafts/*.md` 中 grep —— **命中 0 条**。

## Scope（何时用）

按 glibc 编写、在 musl/OHOS 上构建的项目，引用 glibc 特有符号：

| 符号 | 类型 | glibc | musl | 典型用途 |
|---|---|---|---|---|
| `program_invocation_short_name` | 变量 | ✅ | ❌ | 日志/报错前缀的程序名 |
| `program_invocation_name` | 变量 | ✅ | ❌ | 完整程序路径 |
| `get_current_dir_name()` | 函数 | ✅（扩展）| ❌ | 取当前工作目录（自动 malloc）|

## Symptom

```console
src/udev/udevadm.c:123:9: error: use of undeclared identifier 'program_invocation_short_name'
src/shared/path-util.c:456:5: warning: implicit declaration of function 'get_current_dir_name'
```

**关键特征：跨文件批量出现。** eudev 3.2.14 实测：
`program_invocation_short_name` 涉及 **15 个源文件**（collect / dmi_memory_id /
fido_id / scsi_id / shared-log / udev-udevadm 等），不是单个 TU 的偶然引用。

## Root Cause

OHOS 的 libc 是 **musl**，musl 按 POSIX 最小实现，刻意不提供 glibc 扩展符号。
上游项目（尤其系统工具类）按 glibc 编写时，这些符号在编译期即缺失。

与「内核缺 syscall」（E051）、「socket 结构缺失」（E086/E102）不同，
本条是**纯粹 libc 符号层**的缺口，处置方式为**宏替代或替代实现**，
不涉及内核行为。

## Recommended Solution

### 主方案（priority 1）— 先枚举，再按符号类型统一处置

**第一步：全树枚举引用点**（含头文件间接引用）

```bash
grep -rlnE "program_invocation_short_name|program_invocation_name|get_current_dir_name" <src>/ | wc -l
```

**第二步：按符号类型处置**（均为无条件纯 C 定义，**不得使用平台条件编译宏 —— R8**）

① **变量类**（`program_invocation_short_name`）—— 在配方侧编译一个 compat
   翻译单元**直接定义该符号**，并链接进所有目标（无需改上游源码，也不引入
   任何 `#ifdef`）：

```c
/* compat_progname.c — 无条件定义，由配方加入所有可执行目标 */
char *program_invocation_short_name = "udev";
char *program_invocation_name = "udev";
```

   如项目已有公共头，也可在公共头**无条件** `#define` 指向项目自备的等价变量
   （从 `argv[0]` 取 basename），同样不含条件编译宏。

   ⚠️ 注意：**不要把 `__progname` 当作现成替代**。OHOS 的 `libc.so` 确实导出
   该符号（`nm -D .../libc.so | grep progname` 可见 `B __progname`），但其
   **头文件并不声明**它——直接引用会报
   `error: use of undeclared identifier '__progname'`（实测）。若要使用须自备
   `extern char *__progname;`，且其语义是**启动路径**而非稳定程序名；直接定义
   一个明确取值的符号更稳妥。

② **函数类**（`get_current_dir_name`）—— 提供 POSIX 等价实现放入公共 util
   文件，同样无条件：

```c
/* 无条件实现；musl 的 getcwd 已支持 NULL 自动分配（POSIX.1-2008） */
char *get_current_dir_name(void) { return getcwd(NULL, 0); }
```

**关键**：优先放在**公共头/compat 翻译单元**（eudev 放 `src/udev/udev.h` 的
等价位），一处定义全局生效，避免 15 个文件逐个重复。

### 回退方案（priority 2）— per-file patch

无公共头可挂宏时，逐文件加**无条件的纯 C 定义**（eudev 存量补丁即此形态）。

- **不得**在补丁中引入平台条件编译宏（R8）——用无条件定义即可，无需 `#ifdef`；
- 标注 `platform_only: True`，不夹带功能改动；
- 写入 manifest `patches_applied` 供审计。

### 禁止做法

- ❌ 把缺符号当"笔误"逐个文件手改 —— 会漏掉未报错文件中的引用点；
- ❌ 等价物选错（如把 argv[0] 全路径当 short_name）—— 运行时日志/行为异常；
- ❌ 用 `-D_GNU_SOURCE` 或改 `-std=` "绕过" —— musl **本身不实现**这些符号，
  该宏只控制头文件暴露，纯属无效。

## 实测证据（2026-09-16，eudev 3.2.14）

| 项 | 结果 |
|---|---|
| 符号分布 | `program_invocation_short_name` 15 个源文件；`get_current_dir_name` 1 处 |
| 存量补丁的实际做法 | 逐文件 `#define program_invocation_short_name "<程序名>"` 字符串字面量（如补丁 0012 用 `"udev"`、0004 用 `"collect"`）；**这就是 eudev 能编译通过的原因** |
| 本条推荐的 R8 合规做法 | 不改上游：由配方编译一个 compat 翻译单元无条件定义该变量，链接进所有目标；函数类提供 `getcwd(NULL,0)` 包装实现 |
| 结果 | 编译通过，`udevadm --version` 输出正常（251），4 项消费者断言全过 |
| 补丁形态 | 0004–0016 共 14 个 platform_only patch（**均为 main 存量**，本 PR 未新增/修改补丁）|

## 测试覆盖边界

本条只处理 **libc 符号缺失**（编译期）。区分相邻情形：

- 内核 syscall 缺失 → `E051`；
- 头文件结构/常量缺失 → `E086` / `E102`；
- 头文件重复定义 → `E091`。

## 关联条目

- 相似：`E051`（syscall）、`E086`（ucred）、`E102`（mmsghdr）、`E091`（sockaddr_storage）
- 差异：见上方差异化定位表
