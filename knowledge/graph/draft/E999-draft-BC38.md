# E999: OpenHarmony musl libc — getprogname() 和 sys/poll.h 适配

## 问题

在 OpenHarmony 上编译某些软件（特别是 Apple/BSD 源码移植项目）时，会遇到两类 musl libc 兼容性问题：

### 1. getprogname() 不可用

```
src/shims/getprogname.h:45:5: error: getprogname(3) is not available on this platform
```

**根因**：OpenHarmony 使用 musl libc，不提供 `getprogname()` 函数和 `program_invocation_name` 变量，但提供 `__progname`（与 Android 类似）。

**解决方案**：在 getprogname shim 中添加 `#ifdef __OHOS__` 守卫，使用 `__progname`：

```c
#ifdef __OHOS__
extern const char *__progname;
#endif

static inline char *
getprogname(void)
{
#if HAVE_DECL_PROGRAM_INVOCATION_SHORT_NAME
    return program_invocation_short_name;
#elif defined(__ANDROID__)
    return __progname;
#elif defined(__OHOS__)
    return (char *)__progname;  // 需要显式类型转换，避免 const char* vs char* -Werror
#else
#   error getprogname(3) is not available on this platform
#endif
}
```

**注意**：`__progname` 是 `const char *` 类型，而 `getprogname()` 返回 `char *`，需要显式类型转换避免 `-Werror`。

### 2. sys/poll.h 重定向

```
/data/service/hnp/.../sys/poll.h:1:2: error: redirecting incorrect #include <sys/poll.h> to <poll.h> [-Werror,-W#warnings]
```

**根因**：musl libc 的 `sys/poll.h` 是一个 redirect header，会触发 `#warning` 导致 `-Werror` 编译失败。

**解决方案**：在相关代码中添加 `#ifdef __OHOS__` 守卫，使用 `#include <poll.h>`：

```c
#ifdef __OHOS__
#include <poll.h>
#else
#include <sys/poll.h>
#endif
```

## 受影响范围

- 使用 `getprogname()` 的软件（libdispatch 等 Apple/BSD 移植项目）
- 使用 `<sys/poll.h>` 的软件（需要 -Werror 编译的软件）
- 所有从 Apple/BSD 生态移植到 OpenHarmony 的项目

## 关联

- E014: syscall/compat — POSIX 函数缺失
- E032: libc compat headers — musl libc header 差异
- E033: musl libc 其他兼容性问题

## 验证

```bash
# 验证 __progname 可用
echo 'extern const char *__progname; int main() { return __progname[0]; }' | clang -x c - -o /dev/null 2>&1

# 验证 poll.h 可用
echo '#include <poll.h>; int main() { return 0; }' | clang -x c - -o /dev/null 2>&1
```