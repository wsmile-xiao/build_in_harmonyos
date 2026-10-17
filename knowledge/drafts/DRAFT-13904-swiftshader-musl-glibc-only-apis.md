# DRAFT-13904：OHOS/musl 缺失 glibc 专属 API（且 `__linux__` 守卫会误命中）

> Status: **Draft**（待审核 promote）| severity: `P1` | category: `platform` | Updated: 2026-09-30
> 对应: `knowledge/drafts/DRAFT-13904-swiftshader-musl-glibc-only-apis.kv`
> 来源 PR: #13904（swiftshader 0_git20260921 适配 HarmonyOS PC）

---

**匹配关键词**：pthread_getaffinity_np, pthread_setaffinity_np, RTLD_DI_ORIGIN, dlinfo, musl, glibc, __OHOS__, __BIONIC__, sched_setaffinity

## 错误签名（error_signature）

```text
use of undeclared identifier 'pthread_(get|set)affinity_np'|use of undeclared identifier 'RTLD_DI_ORIGIN'
```

## 错误摘录（error_excerpt）

```text
third_party/marl/src/thread.cpp:161:7: error: use of undeclared identifier 'pthread_getaffinity_np'
third_party/marl/src/thread.cpp:407:5: error: use of undeclared identifier 'pthread_setaffinity_np'; did you mean 'sched_setaffinity'?
tests/VulkanWrapper/VulkanTester.cpp:236:16: error: use of undeclared identifier 'RTLD_DI_ORIGIN'
```

## 根因（root_cause）

OHOS 使用 **musl libc**。上游代码常见守卫形态：

```c
#elif defined(__linux__) && !defined(__ANDROID__) && !defined(__BIONIC__)
    pthread_getaffinity_np(...);   /* glibc-only */
```

而 OHOS 的 clang 同时预定义 `__OHOS__` **与** `__linux__`/`__unix__`
（target = aarch64-unknown-linux-ohos），且不定义 `__ANDROID__`/`__BIONIC__`
→ 该分支在 OHOS 上为真 → 编译 glibc 专属 API → 失败。
同类：`dlinfo(lib, RTLD_DI_ORIGIN, ...)`（`RTLD_DI_ORIGIN` 是 glibc 扩展）。

## 推荐方案（rec_approach）

1. **能用 POSIX 等价物就用**：musl 提供 `<sched.h>` 的 `cpu_set_t`/`CPU_*` 宏与
   `sched_getaffinity(0,…)`/`sched_setaffinity(0,…)`（pid=0 表示调用线程），
   替换 `pthread_{get,set}affinity_np`：

```c
#if defined(__GLIBC__)
    pthread_getaffinity_np(thread, sizeof(cpu_set_t), &cpuset);
#else
    (void)thread;
    sched_getaffinity(0, sizeof(cpu_set_t), &cpuset);   /* musl / OHOS */
#endif
```

2. **无等价物就按特性守卫**：`#if defined(RTLD_DI_ORIGIN) ... #endif`（或 `#if defined(__GLIBC__)`），
   让 musl 跳过该块。
3. **切忌**把 `defined(__linux__)` 当作 glibc 的同义词；判定 libc 用 `__GLIBC__` / `__OHOS__` / `__MUSL__`。

## 快速自查

```bash
$ clang -dM -E -x c /dev/null | grep -Ei 'linux|ohos|musl|unix'
#define __OHOS__ 1
#define __linux__ 1          # ← 会误导 glibc-only 守卫
#define __unix__ 1
```

grep 上游源码：`pthread_getaffinity_np|pthread_setaffinity_np|RTLD_DI_ORIGIN|mallinfo|execinfo\.h|secure_getenv|__GLIBC__`。

## 适用范围

所有 musl 系平台（OHOS、Alpine、部分嵌入式），尤其是携带 vendored 第三方库（marl/abseil/folly 等）的项目。

---

*本文件由 `knowledge/drafts/DRAFT-13904-swiftshader-musl-glibc-only-apis.kv` 字段派生生成（补齐 kv↔md 配套）；内容与 kv 一致，待主编审核 promote 后转入 `knowledge/doc/`。*
