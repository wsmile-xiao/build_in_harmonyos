# E569 — musl 头文件不传递包含：`<sys/file.h>` 不引入 `<fcntl.h>`，`struct flock` 变 incomplete type

> 状态：草稿（路径 B）。合并/提升由知识库维护流程分配正式编号并生成 `doc/`。
> 来源：`crashmail/1.7`（CrashMail II，内嵌 JAMLIB 的 `src/jamlib/mbase.c`）设备实测 2026-09-10。

## 错误特征

glibc 上一直编译通过的旧代码，在 OHOS/musl 上同一个文件同时报出四类错，
**全部指向同一个 include 缺失**：

```text
mbase.c:506:18: error: variable has incomplete type 'struct flock'
    struct flock fl;
                 ^
mbase.c:506:12: note: forward declaration of 'struct flock'
mbase.c:516:28: error: use of undeclared identifier 'F_WRLCK'
    if(DoLock_I) fl.l_type=F_WRLCK;
mbase.c:517:28: error: use of undeclared identifier 'F_UNLCK'
    else         fl.l_type=F_UNLCK;
mbase.c:524:14: warning: call to undeclared function 'fcntl';
      ISO C99 and later do not support implicit function declarations
    Status_I=fcntl(Handle_I,F_SETLK,&fl);
mbase.c:524:29: error: use of undeclared identifier 'F_SETLK'
    Status_I=fcntl(Handle_I,F_SETLK,&fl);
```

典型特征是"**一个类型不完整 + 三个常量未声明 + 一个函数隐式声明**"同时出现在
文件锁相关的一小段代码里，而源码看起来明明 include 了 `<sys/file.h>`。

## 触发条件

- 构建系统：任意（纯编译期问题）。
- 阶段：compilation。
- 源码使用 `struct flock` / `F_SETLK` / `F_WRLCK` / `F_UNLCK` / `fcntl()`，
  但只写了 `#include <sys/file.h>`（或只写了 `<unistd.h>`），没有显式
  `#include <fcntl.h>`。
- 代码路径由 `__linux__`/`__LINUX__` 之类的 Linux 宏开启——OHOS 上这些宏常为真，
  于是这条 glibc 专属的"隐式可见性假设"在 OHOS 上被激活。

## 根因分析

glibc 的 `<sys/file.h>` 内部会 `#include <fcntl.h>`，因此 `struct flock`
的定义、`F_SETLK`/`F_WRLCK`/`F_UNLCK` 常量、`fcntl()` 的原型全都**间接可见**；
`<unistd.h>` 在 glibc 下也顺带引入部分声明。**musl 不做这种传递包含**：
musl 的 `<sys/file.h>` 只声明 `flock()`/`lockf()` 相关接口，`struct flock` 与
`F_*` 常量定义在 `<fcntl.h>` 里，不经 `<sys/file.h>` 暴露。

于是同一份源码在 glibc 上"碰巧能编"，在 musl/OHOS 上以 incomplete type +
undeclared identifier 的形式失败。这是**头文件可见性假设**问题，不是 OHOS 缺能力：
`struct flock`、`F_SETLK`、`F_SETLK` 对应的 `fcntl(2)` 在 OHOS 上都可用，
只是必须自己 include 正确的头。

## 诊断：一条预处理探针即可定位（不需要看平台文档）

不要靠"glibc 有没有传递包含"的记忆判断，直接问编译器：

```sh
# 只包含嫌疑头，看 struct flock 与 F_SETLK 是否可见
printf '#include <sys/file.h>\nstruct flock fl;\nint x = F_SETLK;\n' > /tmp/p1.c
clang -fsyntax-only /tmp/p1.c && echo "间接可见" || echo "不可见 → 需要显式 include"

printf '#include <fcntl.h>\nstruct flock fl;\nint x = F_SETLK;\n' > /tmp/p2.c
clang -fsyntax-only /tmp/p2.c && echo "fcntl.h 提供定义"
```

对照实验（同一个 clang、同一台设备）：

| 探针 | glibc 环境 | OHOS/musl 环境 |
| --- | --- | --- |
| 仅 `#include <sys/file.h>` | 通过 | **失败**（incomplete type / undeclared） |
| 仅 `#include <fcntl.h>` | 通过 | 通过 |

**第二条互补判据**：`grep -c 'struct flock' <sysroot>/usr/include/sys/file.h` 为 0，
而 `<sysroot>/usr/include/fcntl.h` 里有定义——说明不是平台缺能力，而是可见性。

## 推荐方案

在**原有的条件块内**补一行 `#include <fcntl.h>`，不改任何逻辑、不加平台宏分支：

```diff
 #if defined( __LINUX__ )
 #include <sys/file.h>
+#include <fcntl.h>
 #include <unistd.h>
 #endif
```

要点：

- **放在原有 `#if defined(__LINUX__)` 块内**，不要提到文件顶层——顶层 include 会让
  Win32/OS2 等其它平台分支也吃到 POSIX 头，破坏上游多平台构建。
- 这是**平台中立的最小可移植性修复**：glibc 下重复 include `<fcntl.h>` 无害
  （头文件自带守卫），因此不需要 `#ifdef __OHOS__`（R8 默认禁止平台条件编译）。
- 同类嫌疑头对（glibc 有传递包含、musl 没有）值得一并排查：
  - `<sys/file.h>` → `struct flock` / `F_SETLK` / `LOCK_*`（**本品**）
  - `<sys/socket.h>` → `struct ucred`（另见 E086）
  - `<netinet/in.h>` → 部分 socket 选项常量

## 验证

```sh
# 1) 预处理探针（上节）确认可见性差异，而不是猜测
printf '#include <sys/file.h>\nstruct flock fl;\nint x = F_SETLK;\n' > p.c
clang -fsyntax-only p.c; echo "before rc=$?"       # OHOS: 非 0
printf '#include <sys/file.h>\n#include <fcntl.h>\nstruct flock fl;\nint x = F_SETLK;\n' > p.c
clang -fsyntax-only p.c; echo "after  rc=$?"       # 期望 0

# 2) 补丁后重编该单元应零错误、零 implicit-function-declaration 警告
#    （警告消失是"原型真的可见"的正面证据）
clang -c src/jamlib/mbase.c -o /dev/null 2>&1 | grep -c 'implicit function declaration'   # 期望 0

# 3) 功能级：文件锁真的生效（不是只编过）
#    在 JAM 消息库上做并发打开探针，第二个进程应拿到 JAM_LOCK_FAILED 而不是成功
```

## 禁止做法

- ❌ **加 `-D_GNU_SOURCE` 或抬 `_POSIX_C_SOURCE` 硬凑**：可见性来自**头文件本身**
  是否被包含，不是特性测试宏；抬宏还可能反过来改变其它 API 的可见性，把一处
  编译错误变成多处行为差异。
- ❌ **在源码里手抄 `struct flock` / `#define F_SETLK`**：OHOS 的 `<fcntl.h>` 已经
  提供了正确定义（含 ABI 布局），手抄会引入结构体布局不一致，静默破坏 `fcntl()`
  语义（E115 的 fallocate 常量补齐场景不同：那里确实是内核头未同步）。
- ❌ **用 `#ifdef __OHOS__` 包住补丁**：R8 默认禁止平台条件编译，而这里 glibc/musl
  都接受显式 include，等价方案存在，无需豁免。
- ❌ **只改一处就收工**：同一文件里可能有多个 `__LINUX__` 条件块各自 include 头，
  且 GNU makefile 的每单元独立编译会让"改了一个 .c"看起来就够了——按
  `grep -rn 'struct flock\|F_SETLK\|F_WRLCK' ` 枚举全部使用点后再改。

## 关联条目

- **E086**：同族（musl 不定义 `struct ucred`），但那一条的修法是提供替代实现；
  本品的修法是补 include，因为能力在平台上确实存在。
- **E115**：同样是 fcntl 相关的 OHOS 缺口，但根因是内核头缺常量定义（需补
  `#define`），与本品"头文件可见性"是不同层面，勿混用修法。
- **E133**：musl 头文件被 `-isystem` 遮蔽（搜索路径问题）；本品是**传递包含**
  缺失（头文件内部 include 图问题），两者都表现为"musl 下头文件行为不同"但
  诊断与修法不同。

## 关键词

musl, glibc, sys/file.h, fcntl.h, struct flock, F_SETLK, F_WRLCK, incomplete type, transitive include, header visibility, declaration leak, implicit function declaration, OHOS, portability
