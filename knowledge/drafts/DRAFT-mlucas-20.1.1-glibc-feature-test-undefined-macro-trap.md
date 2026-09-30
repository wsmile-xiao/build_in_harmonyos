# DRAFT-mlucas-20.1.1：__GLIBC__ 在 OHOS/musl 上未定义 ⇒ 在 `#if` 中取值 0 ⇒ glibc 版本门反转

- **触发实例**：mlucas 20.1.1 适配（2026-09-29，OHOS aarch64 / clang 15.0.4 / musl）
- **错误签名**：`fatal error: 'sys/sysctl.h' file not found`（20 个 TU）；`use of undeclared identifier 'cpu_set_t'`（+ `cpu_set` ×4）
- **类别**：portability / libc / headers / platform-guard
- **严重度**：2（编译期直接失败，但根因单一、修复面很小）

## 症状（均为真实编译输出）

```
../src/platform.h:1306:11: fatal error: 'sys/sysctl.h' file not found
        #include <sys/sysctl.h>
                 ^~~~~~~~~~~~~~
../src/threadpool.c:324:3: error: use of undeclared identifier 'cpu_set_t'
                cpu_set_t cpu_set;
                ^
../src/threadpool.c:338:13: warning: call to undeclared function 'sched_setaffinity'
```

## 根因

OHOS 走 musl libc：clang 预定义 `__linux__`（`clang -dM -E -x c /dev/null` 实测），
但**不定义** `__GLIBC__` / `__GLIBC_MINOR__`。

C 预处理规则：`#if` 中未定义的标识符求值为 **0**。于是上游为**旧 glibc** 写的判断

```c
#if defined(OS_TYPE_MACOSX) || !defined(OS_TYPE_GNU_HURD) && ((__GLIBC__ < 2) || (__GLIBC_MINOR__ < 30))
    #include <sys/sysctl.h>
#endif
```

在 musl 上 `(0 < 2)` 恒真 ⇒ 包含 glibc/BSD 专有头 ⇒ 失败。**注意这正好与作者意图相反**：
作者想表达的是"glibc 太老所以用 sysctl"，结果"没有 glibc"也被判成"glibc 太老"。

同理，`threadpool.c` 用 `#elif defined(OS_TYPE_LINUX)` 圈定 CPU 亲和性代码
（`cpu_set_t`/`CPU_ZERO`/`CPU_SET`/`sched_setaffinity`，全部是 glibc 扩展），而
`OS_TYPE_LINUX` 由 `__linux__` 派生 ⇒ OHOS 命中该分支 ⇒ 标识符未声明。

> **模式识别要点**：源码把"缺少某个 glibc 特性"表达成"某个 glibc 宏的数值比较"或
> "是不是 Linux"，这两种写法在 musl 上都会选错分支。

## 最小修复（不含任何平台宏）

1. `src/platform.h` —— 用**能力探测**替代版本判断：

```c
#if defined(OS_TYPE_MACOSX) || !defined(OS_TYPE_GNU_HURD) && ((__GLIBC__ < 2) || (__GLIBC_MINOR__ < 30))
+  #if __has_include(<sys/sysctl.h>)
  #ifdef OS_TYPE_LINUX
	#warning GLIBC either not defined or version < 2.30 ... including <sys/sysctl.h> header.
  #endif
	#include <sys/sysctl.h>
+  #endif
#endif
```

2. `src/threadpool.c` —— 把"是不是 Linux"收紧为"是不是 glibc"，并给非 glibc 的 Linux
   留一个空分支（沿用上游自己对 OpenBSD 的写法）：

```c
-	#elif defined(OS_TYPE_LINUX)
+	#elif defined(OS_TYPE_LINUX) && defined(__GLIBC__)
 	  ... cpu_set_t / sched_setaffinity ...
+	#elif defined(OS_TYPE_LINUX)
+	  // e.g. musl-based libcs provide no CPU-affinity API; leave it to the OS:
+	  #warning This C library provides no CPU-affinity API ... affinity-setting is up to the OS.
 	#elif defined(OS_TYPE_MACOSX)
```

两处修改对 glibc / BSD / macOS 行为**完全不变**，且不触发 R8/PF5 的平台宏限制。

## 为什么不用 `__OHOS__` 守卫

- PF5 会机械拦截 `patches/*.patch` 新增行中的 `__OHOS__`（R8 只对"libc 探针"类例外开口，
  须在 PR 说明）。这里 `__has_include` / `__GLIBC__` 同样准确且**跨平台正确**——如果哪天
  出现另一个 musl 平台（Alpine/musl 交叉工具链），无需再改。
- 也**不要**用编译参数伪造 `-D__GLIBC__=2`：那会污染该 TU 内**所有** glibc 相关判断。

## 验证

| 命令 | 结果 |
|---|---|
| `CC='clang -I<gmp>/include -L<gmp>/lib' bash makemake.sh nosimd` | 修复前 `grep -c "error:" build.log` = 20 且 5；修复后 exit 0 |
| `readelf -d obj_nosimd/Mlucas_nosimd` | 仅 `NEEDED libc.so`（gmp 静态） |
| `conan create archives/m/mlucas/20.1.1 -pr:h=ci/conan/profiles/ohos-aarch64 -r=ohpcd` | exit 0（111s，含 test_package） |

## 适用边界

任何把 glibc 版本号写进 `#if`（`__GLIBC__` / `__GLIBC_MINOR__` / `__GLIBC_PREREQ`）的包，
以及任何用 `defined(__linux__)` 圈定 glibc 专有 API（`sched_setaffinity`/`cpu_set_t`、
`sys/sysctl.h`、`sys/sendfile.h` 等）的包。**这不是上游缺陷**——在 OHOS 上是平台事实。

## 关联

- 配方补丁：`archives/m/mlucas/20.1.1/patches/0001-src-platform.h.patch`、
  `archives/m/mlucas/20.1.1/patches/0002-src-threadpool.c.patch`
- 相似知识：`E086`（__OHOS__ 本地等价实现）、`DRAFT-chipmunk2d-7.0.3-sysctl-apple-guard`
  （同 miss 的另一种修法：收敛到 `__APPLE__`）、
  `DRAFT-msquic-2.6.1-pthread-setaffinity-np-android-guard`
