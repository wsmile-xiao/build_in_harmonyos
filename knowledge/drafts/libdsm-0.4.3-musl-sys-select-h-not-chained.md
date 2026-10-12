# musl 下 fd_set/select/timeval 未声明（use of undeclared identifier 'fd_set'）

> 草稿 ID：`libdsm-0.4.3-musl-sys-select-h-not-chained`
> 来源任务：libdsm 0.4.3 适配（SMB 客户端库，meson 构建，HarmonyOS PC aarch64 conan create 编译期）

## 错误特征

```
../src/netbios_session.c:352:9: error: use of undeclared identifier 'fd_set'
        fd_set read_fds;
        ^
../src/netbios_utils.c:183:5: error: use of undeclared identifier 'fd_set'
    fd_set        read_fds;
    ^
../src/netbios_utils.c:185:20: error: variable has incomplete type 'struct timeval'
        struct timeval timeout = {0, 0};
../src/netbios_session.c:371:5: warning: call to undeclared function 'FD_ZERO'
9 warnings and 20 errors generated.
```

**关键对比**：同一份代码在 glibc/Linux 上编译零告警通过——不是代码"写错了"，
是 glibc 与 musl 的头文件链差异。

## 触发条件

- OHOS（musl libc）交叉编译/原生编译；
- 源码使用 `fd_set` / `select()` / `struct timeval` / `FD_ZERO/FD_SET/FD_ISSET`；
- 但没有 `#include <sys/select.h>`（常见于老网络库：作者在 glibc 上从不需要显式包含）；
- 注意**并非所有文件都挂**：包含 `<sys/time.h>` 的文件不挂（musl 的 sys/time.h
  会带出 fd_set 相关定义），只挂"恰好没包含 sys/time.h 也没包含 sys/select.h"的文件——
  本例 netbios_ns.c（有 sys/time.h）幸免，netbios_session.c/netbios_utils.c 挂。

## 根因

glibc 的 `<sys/types.h>` 通过 `bits/types.h` → `bits/types/struct_timeb.h` 等内部头文件链
**间接包含** `<sys/select.h>`（fd_set/struct timeval/FD_* 的权威声明），所以 glibc 上
"只 include 了 sys/socket.h 也能用 fd_set"。musl 严格按 POSIX 分层，`sys/types.h`
不链 sys/select.h，未显式包含就报 undeclared。

## 修复（portability 补丁）

为每个使用 fd_set 但未包含该头的文件补 `#include <sys/select.h>`：

```diff
--- a/src/netbios_session.c
+++ b/src/netbios_session.c
@@ -47,6 +47,7 @@
 #endif
 #include <fcntl.h>
 #include <errno.h>
+#include <sys/select.h>

 #include "smb_defs.h"
--- a/src/netbios_utils.c
+++ b/src/netbios_utils.c
@@ -41,6 +41,7 @@
 #ifdef NS_ABORT_USE_PIPE
 #include <unistd.h>
 #include <fcntl.h>
+#include <sys/select.h>
 #endif
```

对 glibc/Linux **无害**（重复包含有 include guard），是纯增益的 portability 补丁。

## 反例（不要这么做）

- ❌ 改用 `poll()` 重写源码——过度工程，portability 补丁一行就修；
- ❌ 全局 `-D_SYS_SELECT` 之类伪造——不存在的宏，编译器照样找不到声明；
- ❌ 只给一个文件补——要 grep 全部用 fd_set 的文件（`grep -ln "fd_set\|select(\|struct timeval" src/*.c`）。

## 验证

```bash
# 修复前：conan create 编译期 20 errors
$ conan create -pr:h=~/.conan2/profiles/ohos-aarch64 archives/l/libdsm/0.4.3
error: use of undeclared identifier 'fd_set' × N

# 修复后：
$ conan create -pr:h=~/.conan2/profiles/ohos-aarch64 archives/l/libdsm/0.4.3
libdsm/0.4.3: Package created ... test_package 8/8 断言通过
```

## 证据

- 失败现场：本机 conan create 首跑日志（20 errors，netbios_session.c/netbios_utils.c）
- 修复补丁：`archives/l/libdsm/0.4.3/patches/0001-musl-include-sys-select-h-for-fd_set.patch`
- 平台探测：`gnu11+_GNU_SOURCE` 与 `gnu11+POSIX2008` 两个方言组合的声明可见性实测
  （fd_set 均不可见 → 证明与方言无关，纯头文件链差异）
- 配方实现：`archives/l/libdsm/0.4.3/conanfile.py`
- 适配笔记：`archives/l/libdsm/0.4.3/notes.md`
