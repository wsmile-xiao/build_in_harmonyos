# DRAFT-fex-emu-2608-ohos-musl-uapi-runtime-differences：OHOS 与 glibc 的差异族——逐项定性而非「平台不支持」收尾

> Contributor: Hawkninja21 | Status: Draft | Updated: 2026-09-30
> Source: FEX-Emu 2608 适配 HarmonyOS PC（路径C 高难度挑战，分支 feat/fex-emu-2608）
> 对应：`knowledge/drafts/DRAFT-fex-emu-2608-ohos-musl-uapi-runtime-differences.kv`

## 现象：一批"看起来都是平台不支持"的错误

把一个 Linux 原生项目（x86→AArch64 用户态重编译器 FEX-Emu）搬到 OHOS PC，编译期会撞到一组互不相关的报错。
它们都容易被一句"OHOS 不支持"带过，但**每一类都有确定的修法**：

```text
x32/Types.h:1148: use of undeclared identifier 'SIGEV_THREAD_ID'
x32/Types.h:1149: no member named '_sigev_un' in 'sigevent'
linux/socket.h:23: error: redefinition of 'sockaddr_storage'
Syscalls/Info.cpp:52: use of undeclared identifier 'UNAME26'
CodeCache.cpp:882: use of undeclared identifier 'MREMAP_DONTUNMAP'
（运行期）Couldn't allocate page after SBRK.
（测试脚本）nasm: symbol `et.data_vecs' not defined
```

## 逐项定性与修法

### ① sigevent：musl 与 glibc 的结构差异（不是"没有信号支持"）

OHOS `<signal.h>`：

```c
struct sigevent {
  union sigval sigev_value; int sigev_signo; int sigev_notify;
  void (*sigev_notify_function)(union sigval);
  pthread_attr_t *sigev_notify_attributes;
  char __pad[56-3*sizeof(long)];
};
```

没有 glibc 的 `_sigev_un` 联合体、没有 thread-id 槽、没有 `SIGEV_THREAD_ID`。

**陷阱**：上游的写法是"若 `sigev_notify_thread_id` 未定义就自定义成 `_sigev_un._tid`"。
在 musl 下 `sigev_notify_thread_id` 是**结构体成员名而不是宏**，所以 `#ifndef` 成立、
宏被错误定义，随后 `val.sigev_notify_thread_id` 展开为不存在的 `val._sigev_un._tid`。

修法：用 `__GLIBC__` 分支；非 glibc 上补 `SIGEV_THREAD_ID=4`，并把 thread-id 赋值
包在能力宏里（`FEX_HOST_SIGEVENT_HAS_THREAD_ID`），如实记录 guest 的
`SIGEV_THREAD_ID` 在 OHOS 无法映射。

### ② 内核 uapi 常量缺失

```cpp
#ifndef UNAME26
#define UNAME26 0x0020000        /* Linux personality flag */
#endif
#ifndef MREMAP_DONTUNMAP
#define MREMAP_DONTUNMAP 4       /* Linux 5.7+ */
#endif
```

### ③ sysroot 头无守卫导致重定义

OHOS 的 `sys/socket.h` 用 `#ifndef __MUSL__` 守卫 `sockaddr_storage`，但 OHOS clang
**默认不定义 `__MUSL__`**（实测只定义 `__OHOS__`/`__OHOS_FAMILY__`）；而
`linux/socket.h` 完全无守卫。于是"先 libc 头、后 `linux/wireless.h`"即重定义。

修法（落在项目码里，不动平台头）：引入 uapi 头前临时定义其守卫宏，用完 `#undef`；
先核实该 uapi 头只提供 `struct sockaddr` 这类已由 libc 头提供的符号。

```cpp
#define _UAPI_LINUX_SOCKET_H
#include <linux/wireless.h>
#undef _UAPI_LINUX_SOCKET_H
```

### ④ `MAP_FIXED_NOREPLACE` 在 OHOS 返回 ENOSYS

实测：

```text
sbrk(0)=0x57f18c6000
mmap NOREPLACE=0xffffffffffffffff errno=38(Function not implemented)
mmap FIXED    =0x57f18c6000        errno=0
```

FEX 启动时用它"在 brk 之后顶一页、阻止 sbrk 继续生长"，拿不到就直接 `trap`，
于是可执行文件连 `--help` 都跑不了。

修法：先试 NOREPLACE，`errno==ENOSYS||EINVAL` 时回退 `MAP_FIXED`——
目标页由**当前 brk** 推出、必然在 brk 之上，且这是单线程早启动阶段，
替换是安全的（注释写清前提）。

### ⑤ 用户态工具：toybox sed 的 `a\` 语义

`/usr/bin/sed` 是 **toybox 0.8.12**（非 GNU sed）。`sed -e '$a\ret\n'` 本意追加
`ret`，toybox 把 `\r` 解释为回车 → 实际写入 `CR + "et"`：

```text
$ od -c <generated>.asm_TMP.asm | tail -2
 ... 0 \n  \r e t \n \n
```

这会在汇编源里凭空造出一个标签 `et`，让"前向引用的局部标签"失效，nasm 报
`symbol 'et.data_vecs' not defined`。

修法：改用对实现不敏感的 `s` 命令——`-e '$s/$/\nret/'`（GNU/toybox 均正确）。
CMake 里还要注意 ninja 的 `$` 需写成 `$$`：

```cmake
COMMAND "sed" ARGS "-i" "-e" "\'1s;^;BITS 64\\n;\'" "-e" "\'\$\$s/\$\$/\\nret/\'" "${TMP_FILE}"
```

### ⑥ `/tmp` 只读 → 测试里的 `P_tmpdir`

```text
$ touch /tmp/x ; → Read-only file system
$ ./probe → P_tmpdir=/tmp ; TMPDIR=/storage/Users/currentUser/tmp ; mkstemp(/tmp/...) -> -1
```

`tmpfile()` 与 `mkstemp(P_tmpdir "/...")` 都会失败，而测试里常写成 `abort()`，
于是表现为莫名其妙的 SIGABRT。

修法：临时目录选择改为"优先 `TMPDIR`，否则 `P_tmpdir`"；`tmpfile()` 换成
`mkstemp(TMPDIR/prefixXXXXXX)` + `fdopen` + `unlink`（保持匿名文件语义）。

## 教训

- **先分类再动手**：这一族错误横跨 ABI 布局、uapi、内核特性、用户态工具、文件系统
  五个层次，"平台不支持"会同时掩盖五种可修的问题。
- **对照实验是唯一依据**：例如"ENOSYS vs 权限"用最小 C 程序打 errno 即可判定；
  "sed 语义"用 `od -c` 看实际字节即可判定。
- **不许改平台**：修法必须落在项目码/构建脚本，`/usr/bin/sed`、`/tmp`、
  sysroot 头都不是可改对象。
