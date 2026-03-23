# musl libc vs glibc：ISO C + POSIX 全量接口对比表

> **版本**: 1.0.0  
> **生成日期**: 2026-03-23  
> **适用范围**: musl 1.2.x / glibc 2.31+ / OpenHarmony musl (基于 1.2.x)  
> **说明**: 本表逐接口列出 glibc、musl 和 OpenHarmony musl 的支持状态。  
> **图例**: ✅ 完整支持 | ⚠️ 部分支持/行为差异 | ❌ 不支持 | 🔧 OHOS 增强补充 | ➕ musl 独有扩展

---

## 第一部分：ISO C 标准接口

### 总览

| C 标准 | glibc 覆盖 | musl 覆盖 | OHOS musl 覆盖 |
|--------|:----------:|:---------:|:--------------:|
| C89/C90 | 100% | ~100% | ~100% |
| C95 | 100% | 100% | 100% |
| C99 | 100% | ~100% | ~100% |
| C11 | ~99% | ~99% | ~99% |
| C17 | ~99% | ~98% | ~98% |
| C23 | ~90% | ~85% | ~85% |

---

## 1.1 C89/C90 标准接口

### 1.1.1 `<assert.h>`

| 接口/宏 | 类型 | glibc | musl | OHOS | 说明 |
|---------|------|:-----:|:----:|:----:|------|
| `assert` | 宏 | ✅ | ✅ | ✅ | |
| `NDEBUG` | 宏 | ✅ | ✅ | ✅ | |

### 1.1.2 `<ctype.h>`

| 接口 | 类型 | glibc | musl | OHOS | 说明 |
|------|------|:-----:|:----:|:----:|------|
| `isalnum` | 函数 | ✅ | ✅ | ✅ | |
| `isalpha` | 函数 | ✅ | ✅ | ✅ | |
| `isblank` | C99 | ✅ | ✅ | ✅ | |
| `iscntrl` | 函数 | ✅ | ✅ | ✅ | |
| `isdigit` | 函数 | ✅ | ✅ | ✅ | |
| `isgraph` | 函数 | ✅ | ✅ | ✅ | |
| `islower` | 函数 | ✅ | ✅ | ✅ | |
| `isprint` | 函数 | ✅ | ✅ | ✅ | |
| `ispunct` | 函数 | ✅ | ✅ | ✅ | |
| `isspace` | 函数 | ✅ | ✅ | ✅ | |
| `isupper` | 函数 | ✅ | ✅ | ✅ | |
| `isxdigit` | 函数 | ✅ | ✅ | ✅ | |
| `tolower` | 函数 | ✅ | ✅ | ✅ | |
| `toupper` | 函数 | ✅ | ✅ | ✅ | |
| `toascii` | GNU/BSD | ✅ | ✅ | ✅ | musl 通过 _GNU_SOURCE 提供 |

### 1.1.3 `<errno.h>`

| 接口/宏 | 类型 | glibc | musl | OHOS | 说明 |
|---------|------|:-----:|:----:|:----:|------|
| `errno` | 宏/变量 | ✅ | ✅ | ✅ | glibc 线程安全宏; musl 线程本地变量 |
| `EDOM` | 宏 | ✅ | ✅ | ✅ | |
| `ERANGE` | 宏 | ✅ | ✅ | ✅ | |
| `E2BIG` | 宏 | ✅ | ✅ | ✅ | |
| `EACCES` | 宏 | ✅ | ✅ | ✅ | |
| `EADDRINUSE` | 宏 | ✅ | ✅ | ✅ | |
| `EADDRNOTAVAIL` | 宏 | ✅ | ✅ | ✅ | |
| `EAFNOSUPPORT` | 宏 | ✅ | ✅ | ✅ | |
| `EAGAIN` | 宏 | ✅ | ✅ | ✅ | |
| `EALREADY` | 宏 | ✅ | ✅ | ✅ | |
| `EBADF` | 宏 | ✅ | ✅ | ✅ | |
| `EBADMSG` | 宏 | ✅ | ✅ | ✅ | |
| `EBUSY` | 宏 | ✅ | ✅ | ✅ | |
| `ECANCELED` | 宏 | ✅ | ✅ | ✅ | |
| `ECHILD` | 宏 | ✅ | ✅ | ✅ | |
| `ECONNABORTED` | 宏 | ✅ | ✅ | ✅ | |
| `ECONNREFUSED` | 宏 | ✅ | ✅ | ✅ | |
| `ECONNRESET` | 宏 | ✅ | ✅ | ✅ | |
| `EDEADLK` | 宏 | ✅ | ✅ | ✅ | |
| `EDESTADDRREQ` | 宏 | ✅ | ✅ | ✅ | |
| `EDQUOT` | 宏 | ✅ | ✅ | ✅ | |
| `EEXIST` | 宏 | ✅ | ✅ | ✅ | |
| `EFAULT` | 宏 | ✅ | ✅ | ✅ | |
| `EFBIG` | 宏 | ✅ | ✅ | ✅ | |
| `EHOSTUNREACH` | 宏 | ✅ | ✅ | ✅ | |
| `EIDRM` | 宏 | ✅ | ✅ | ✅ | |
| `EILSEQ` | 宏 | ✅ | ✅ | ✅ | |
| `EINPROGRESS` | 宏 | ✅ | ✅ | ✅ | |
| `EINTR` | 宏 | ✅ | ✅ | ✅ | |
| `EINVAL` | 宏 | ✅ | ✅ | ✅ | |
| `EIO` | 宏 | ✅ | ✅ | ✅ | |
| `EISCONN` | 宏 | ✅ | ✅ | ✅ | |
| `EISDIR` | 宏 | ✅ | ✅ | ✅ | |
| `ELOOP` | 宏 | ✅ | ✅ | ✅ | |
| `EMFILE` | 宏 | ✅ | ✅ | ✅ | |
| `EMLINK` | 宏 | ✅ | ✅ | ✅ | |
| `EMSGSIZE` | 宏 | ✅ | ✅ | ✅ | |
| `ENAMETOOLONG` | 宏 | ✅ | ✅ | ✅ | |
| `ENETDOWN` | 宏 | ✅ | ✅ | ✅ | |
| `ENETRESET` | 宏 | ✅ | ✅ | ✅ | |
| `ENETUNREACH` | 宏 | ✅ | ✅ | ✅ | |
| `ENFILE` | 宏 | ✅ | ✅ | ✅ | |
| `ENOBUFS` | 宏 | ✅ | ✅ | ✅ | |
| `ENODATA` | 宏 | ✅ | ✅ | ✅ | XSI 扩展 |
| `ENODEV` | 宏 | ✅ | ✅ | ✅ | |
| `ENOENT` | 宏 | ✅ | ✅ | ✅ | |
| `ENOEXEC` | 宏 | ✅ | ✅ | ✅ | |
| `ENOLCK` | 宏 | ✅ | ✅ | ✅ | |
| `ENOLINK` | 宏 | ✅ | ✅ | ✅ | |
| `ENOMEM` | 宏 | ✅ | ✅ | ✅ | |
| `ENOMSG` | 宏 | ✅ | ✅ | ✅ | |
| `ENOPROTOOPT` | 宏 | ✅ | ✅ | ✅ | |
| `ENOSPC` | 宏 | ✅ | ✅ | ✅ | |
| `ENOSR` | 宏 | ✅ | ✅ | ✅ | |
| `ENOSTR` | 宏 | ✅ | ✅ | ✅ | |
| `ENOSYS` | 宏 | ✅ | ✅ | ✅ | |
| `ENOTCONN` | 宏 | ✅ | ✅ | ✅ | |
| `ENOTDIR` | 宏 | ✅ | ✅ | ✅ | |
| `ENOTEMPTY` | 宏 | ✅ | ✅ | ✅ | |
| `ENOTRECOVERABLE` | 宏 | ✅ | ✅ | ✅ | |
| `ENOTSOCK` | 宏 | ✅ | ✅ | ✅ | |
| `ENOTSUP` | 宏 | ✅ | ✅ | ✅ | |
| `ENOTTY` | 宏 | ✅ | ✅ | ✅ | |
| `ENXIO` | 宏 | ✅ | ✅ | ✅ | |
| `EOPNOTSUPP` | 宏 | ✅ | ✅ | ✅ | |
| `EOVERFLOW` | 宏 | ✅ | ✅ | ✅ | |
| `EOWNERDEAD` | 宏 | ✅ | ✅ | ✅ | |
| `EPERM` | 宏 | ✅ | ✅ | ✅ | |
| `EPFNOSUPPORT` | 宏 | ✅ | ✅ | ✅ | |
| `EPIPE` | 宏 | ✅ | ✅ | ✅ | |
| `EPROTO` | 宏 | ✅ | ✅ | ✅ | |
| `EPROTONOSUPPORT` | 宏 | ✅ | ✅ | ✅ | |
| `EPROTOTYPE` | 宏 | ✅ | ✅ | ✅ | |
| `ERANGE` | 宏 | ✅ | ✅ | ✅ | |
| `EROFS` | 宏 | ✅ | ✅ | ✅ | |
| `ESPIPE` | 宏 | ✅ | ✅ | ✅ | |
| `ESRCH` | 宏 | ✅ | ✅ | ✅ | |
| `ESTALE` | 宏 | ✅ | ✅ | ✅ | |
| `ETIME` | 宏 | ✅ | ✅ | ✅ | |
| `ETIMEDOUT` | 宏 | ✅ | ✅ | ✅ | |
| `ETXTBSY` | 宏 | ✅ | ✅ | ✅ | |
| `EWOULDBLOCK` | 宏 | ✅ | ✅ | ✅ | 通常等同于 EAGAIN |
| `EXDEV` | 宏 | ✅ | ✅ | ✅ | |

> **说明**: glibc 和 musl 的 errno 值与 Linux 内核保持一致。musl 完整支持所有标准 errno 值。差异在于实现方式：glibc 使用宏展开为 `(*__errno_location())`，musl 使用线程本地存储 `__thread int errno`。


### 1.1.4 `<float.h>`

| 接口/宏 | glibc | musl | OHOS | 说明 |
|---------|:-----:|:----:|:----:|------|
| `FLT_RADIX` | ✅ | ✅ | ✅ | |
| `FLT_MANT_DIG` | ✅ | ✅ | ✅ | |
| `FLT_DIG` | ✅ | ✅ | ✅ | |
| `FLT_EPSILON` | ✅ | ✅ | ✅ | |
| `FLT_MIN` | ✅ | ✅ | ✅ | |
| `FLT_MAX` | ✅ | ✅ | ✅ | |
| `FLT_ROUNDS` | ✅ | ✅ | ✅ | |
| `DBL_MANT_DIG` | ✅ | ✅ | ✅ | |
| `DBL_DIG` | ✅ | ✅ | ✅ | |
| `DBL_EPSILON` | ✅ | ✅ | ✅ | |
| `DBL_MIN` | ✅ | ✅ | ✅ | |
| `DBL_MAX` | ✅ | ✅ | ✅ | |
| `LDBL_MANT_DIG` | ✅ | ✅ | ✅ | |
| `LDBL_DIG` | ✅ | ✅ | ✅ | |
| `LDBL_EPSILON` | ✅ | ✅ | ✅ | |
| `LDBL_MIN` | ✅ | ✅ | ✅ | |
| `LDBL_MAX` | ✅ | ✅ | ✅ | |
| `FLT_HAS_SUBNORM` | C17 | ✅ | ✅ | ✅ | |
| `DBL_HAS_SUBNORM` | C17 | ✅ | ✅ | ✅ | |
| `LDBL_HAS_SUBNORM` | C17 | ✅ | ✅ | ✅ | |
| `FLT_DECIMAL_DIG` | C17 | ✅ | ✅ | ✅ | |
| `DBL_DECIMAL_DIG` | C17 | ✅ | ✅ | ✅ | |
| `LDBL_DECIMAL_DIG` | C17 | ✅ | ✅ | ✅ | |
| `FLT_MIN_EXP` | ✅ | ✅ | ✅ | |
| `FLT_MAX_EXP` | ✅ | ✅ | ✅ | |
| `FLT_MIN_10_EXP` | ✅ | ✅ | ✅ | |
| `FLT_MAX_10_EXP` | ✅ | ✅ | ✅ | |
| `DBL_MIN_EXP` | ✅ | ✅ | ✅ | |
| `DBL_MAX_EXP` | ✅ | ✅ | ✅ | |
| `DBL_MIN_10_EXP` | ✅ | ✅ | ✅ | |
| `DBL_MAX_10_EXP` | ✅ | ✅ | ✅ | |
| `LDBL_MIN_EXP` | ✅ | ✅ | ✅ | |
| `LDBL_MAX_EXP` | ✅ | ✅ | ✅ | |
| `LDBL_MIN_10_EXP` | ✅ | ✅ | ✅ | |
| `LDBL_MAX_10_EXP` | ✅ | ✅ | ✅ | |
| `DECIMAL_DIG` | C99 | ✅ | ✅ | ✅ | |
| `FLT_EVAL_METHOD` | C99 | ✅ | ✅ | ✅ | glibc 默认0; musl aarch64 默认0 |
| `FLT_TRUE_MIN` | C11 | ✅ | ✅ | ✅ | 最小正次正规数 |
| `DBL_TRUE_MIN` | C11 | ✅ | ✅ | ✅ | |
| `LDBL_TRUE_MIN` | C11 | ✅ | ✅ | ✅ | |

### 1.1.5 `<limits.h>`

| 接口/宏 | glibc | musl | OHOS | 说明 |
|---------|:-----:|:----:|:----:|------|
| `CHAR_BIT` | ✅ | ✅ | ✅ | 通常为 8 |
| `CHAR_MIN` | ✅ | ✅ | ✅ | |
| `CHAR_MAX` | ✅ | ✅ | ✅ | |
| `SCHAR_MIN` | ✅ | ✅ | ✅ | |
| `SCHAR_MAX` | ✅ | ✅ | ✅ | |
| `UCHAR_MAX` | ✅ | ✅ | ✅ | |
| `SHRT_MIN` | ✅ | ✅ | ✅ | |
| `SHRT_MAX` | ✅ | ✅ | ✅ | |
| `USHRT_MAX` | ✅ | ✅ | ✅ | |
| `INT_MIN` | ✅ | ✅ | ✅ | |
| `INT_MAX` | ✅ | ✅ | ✅ | |
| `UINT_MAX` | ✅ | ✅ | ✅ | |
| `LONG_MIN` | ✅ | ✅ | ✅ | |
| `LONG_MAX` | ✅ | ✅ | ✅ | |
| `ULONG_MAX` | ✅ | ✅ | ✅ | |
| `LLONG_MIN` | C99 | ✅ | ✅ | ✅ | |
| `LLONG_MAX` | C99 | ✅ | ✅ | ✅ | |
| `ULLONG_MAX` | C99 | ✅ | ✅ | ✅ | |
| `MB_LEN_MAX` | ✅ | ✅ | ✅ | |
| `LINE_MAX` | POSIX | ✅ | ✅ | ✅ | |
| `PTHREAD_KEYS_MAX` | POSIX | ✅ | ✅ | ✅ | |
| `PTHREAD_STACK_MIN` | POSIX | ✅ | ✅ | ✅ | |
| `PTHREAD_THREADS_MAX` | POSIX | ✅ | ✅ | ✅ | |
| `ARG_MAX` | POSIX | ✅ | ✅ | ✅ | |
| `NAME_MAX` | POSIX | ✅ | ✅ | ✅ | |
| `PATH_MAX` | POSIX | ✅ | ✅ | ✅ | |
| `HOST_NAME_MAX` | POSIX | ✅ | ✅ | ✅ | |
| `TZNAME_MAX` | POSIX | ✅ | ✅ | ✅ | |
| `SSIZE_MAX` | POSIX | ✅ | ✅ | ✅ | |
| `NGROUPS_MAX` | POSIX | ✅ | ✅ | ✅ | |
| `OPEN_MAX` | POSIX | ✅ | ✅ | ✅ | |
| `PIPE_BUF` | POSIX | ✅ | ✅ | ✅ | |
| `WORD_BIT` | GNU/BSD | ✅ | ✅ | ✅ | |
| `LONG_BIT` | GNU/BSD | ✅ | ✅ | ✅ | |

### 1.1.6 `<locale.h>`

| 接口/宏 | glibc | musl | OHOS | 说明 |
|---------|:-----:|:----:|:----:|------|
| `setlocale` | ✅ | ✅ | ✅ | glibc 支持完整 locale 数据; musl 仅 C/C.UTF-8 |
| `localeconv` | ✅ | ✅ | ✅ | |
| `LC_ALL` | ✅ | ✅ | ✅ | |
| `LC_COLLATE` | ✅ | ✅ | ✅ | |
| `LC_CTYPE` | ✅ | ✅ | ✅ | |
| `LC_MESSAGES` | ✅ | ✅ | ✅ | |
| `LC_MONETARY` | ✅ | ✅ | ✅ | |
| `LC_NUMERIC` | ✅ | ✅ | ✅ | |
| `LC_TIME` | ✅ | ✅ | ✅ | |
| `NULL` | ✅ | ✅ | ✅ | |
| `struct lconv` | ✅ | ✅ | ✅ | |
| `locale_t` | POSIX | ✅ | ✅ | ✅ | |
| `newlocale` | POSIX | ✅ | ✅ | ✅ | |
| `freelocale` | POSIX | ✅ | ✅ | ✅ | |
| `duplocale` | POSIX | ✅ | ✅ | ✅ | |
| `uselocale` | POSIX | ✅ | ✅ | ✅ | |

> **关键差异**: glibc 包含完整 locale 数据包（200+ locale），支持运行时切换。musl 仅支持 `C` 和 `C.UTF-8`（musl 1.2.2+），`setlocale(LC_ALL, "zh_CN.UTF-8")` 在 musl 上将失败返回 NULL。

### 1.1.7 `<math.h>` (C89 部分)

| 接口 | glibc | musl | OHOS | 说明 |
|------|:-----:|:----:|:----:|------|
| `sin` | ✅ | ✅ | ✅ | |
| `cos` | ✅ | ✅ | ✅ | |
| `tan` | ✅ | ✅ | ✅ | |
| `asin` | ✅ | ✅ | ✅ | |
| `acos` | ✅ | ✅ | ✅ | |
| `atan` | ✅ | ✅ | ✅ | |
| `atan2` | ✅ | ✅ | ✅ | |
| `sinh` | ✅ | ✅ | ✅ | |
| `cosh` | ✅ | ✅ | ✅ | |
| `tanh` | ✅ | ✅ | ✅ | |
| `exp` | ✅ | ✅ | ✅ | |
| `log` | ✅ | ✅ | ✅ | |
| `log10` | ✅ | ✅ | ✅ | |
| `pow` | ✅ | ✅ | ✅ | |
| `sqrt` | ✅ | ✅ | ✅ | |
| `ceil` | ✅ | ✅ | ✅ | |
| `floor` | ✅ | ✅ | ✅ | |
| `fabs` | ✅ | ✅ | ✅ | |
| `ldexp` | ✅ | ✅ | ✅ | |
| `frexp` | ✅ | ✅ | ✅ | |
| `modf` | ✅ | ✅ | ✅ | |
| `fmod` | ✅ | ✅ | ✅ | |
| `abs` | ✅ | ✅ | ✅ | |
| `labs` | ✅ | ✅ | ✅ | |
| `div` | ✅ | ✅ | ✅ | |
| `ldiv` | ✅ | ✅ | ✅ | |
| `rand` | ✅ | ✅ | ✅ | |
| `srand` | ✅ | ✅ | ✅ | |
| `HUGE_VAL` | ✅ | ✅ | ✅ | |
| `RAND_MAX` | ✅ | ✅ | ✅ | glibc: 2^31-1; musl: 2^31-1 |
| `M_E` | GNU | ✅ | ✅ | ✅ | |
| `M_PI` | GNU | ✅ | ✅ | ✅ | |
| `M_LN2` | GNU | ✅ | ✅ | ✅ | |
| `M_LN10` | GNU | ✅ | ✅ | ✅ | |
| `M_SQRT2` | GNU | ✅ | ✅ | ✅ | |
| `M_PI_2` | GNU | ✅ | ✅ | ✅ | |
| `M_PI_4` | GNU | ✅ | ✅ | ✅ | |
| `M_1_PI` | GNU | ✅ | ✅ | ✅ | |
| `M_2_PI` | GNU | ✅ | ✅ | ✅ | |
| `M_2_SQRTPI` | GNU | ✅ | ✅ | ✅ | |
| `M_SQRT1_2` | GNU | ✅ | ✅ | ✅ | |

### 1.1.8 `<setjmp.h>`

| 接口 | glibc | musl | OHOS | 说明 |
|------|:-----:|:----:|:----:|------|
| `setjmp` | ✅ | ✅ | ✅ | ⚠️ 信号掩码保存行为不同（见开发者影响分析） |
| `longjmp` | ✅ | ✅ | ✅ | |
| `jmp_buf` | ✅ | ✅ | ✅ | |
| `sigsetjmp` | POSIX | ✅ | ✅ | ✅ | |
| `siglongjmp` | POSIX | ✅ | ✅ | ✅ | |
| `sigjmp_buf` | POSIX | ✅ | ✅ | ✅ | |

### 1.1.9 `<signal.h>` (C89 部分)

| 接口/宏 | glibc | musl | OHOS | 说明 |
|---------|:-----:|:----:|:----:|------|
| `signal` | ✅ | ✅ | ✅ | |
| `raise` | ✅ | ✅ | ✅ | |
| `SIG_DFL` | ✅ | ✅ | ✅ | |
| `SIG_IGN` | ✅ | ✅ | ✅ | |
| `SIG_ERR` | ✅ | ✅ | ✅ | |
| `SIGABRT` | ✅ | ✅ | ✅ | |
| `SIGFPE` | ✅ | ✅ | ✅ | |
| `SIGILL` | ✅ | ✅ | ✅ | |
| `SIGINT` | ✅ | ✅ | ✅ | |
| `SIGSEGV` | ✅ | ✅ | ✅ | |
| `SIGTERM` | ✅ | ✅ | ✅ | |
| `sig_atomic_t` | ✅ | ✅ | ✅ | |
| `va_list` | ✅ | ✅ | ✅ | |
| `SIGINT` | ✅ | ✅ | ✅ | |
| `SIGKILL` | POSIX | ✅ | ✅ | ✅ | |
| `SIGSTOP` | POSIX | ✅ | ✅ | ✅ | |
| `SIGCONT` | POSIX | ✅ | ✅ | ✅ | |
| `SIGPIPE` | POSIX | ✅ | ✅ | ✅ | |
| `SIGHUP` | POSIX | ✅ | ✅ | ✅ | |
| `SIGQUIT` | POSIX | ✅ | ✅ | ✅ | |
| `SIGTRAP` | POSIX | ✅ | ✅ | ✅ | |
| `SIGUSR1` | POSIX | ✅ | ✅ | ✅ | |
| `SIGUSR2` | POSIX | ✅ | ✅ | ✅ | |
| `SIGBUS` | POSIX | ✅ | ✅ | ✅ | |
| `SIGSYS` | POSIX | ✅ | ✅ | ✅ | |
| `SIGALRM` | POSIX | ✅ | ✅ | ✅ | |


### 1.1.10 `<stdarg.h>`

| 接口/类型 | glibc | musl | OHOS | 说明 |
|-----------|:-----:|:----:|:----:|------|
| `va_start` | ✅ | ✅ | ✅ | |
| `va_end` | ✅ | ✅ | ✅ | |
| `va_arg` | ✅ | ✅ | ✅ | |
| `va_copy` | C99 | ✅ | ✅ | ✅ | |
| `va_list` | ✅ | ✅ | ✅ | |

### 1.1.11 `<stddef.h>`

| 接口/类型 | glibc | musl | OHOS | 说明 |
|-----------|:-----:|:----:|:----:|------|
| `size_t` | ✅ | ✅ | ✅ | |
| `ptrdiff_t` | ✅ | ✅ | ✅ | |
| `wchar_t` | ✅ | ✅ | ✅ | |
| `offsetof` | ✅ | ✅ | ✅ | |
| `NULL` | ✅ | ✅ | ✅ | |
| `max_align_t` | C11 | ✅ | ✅ | ✅ | |
| `wint_t` | C95 | ✅ | ✅ | ✅ | |
| `wctype_t` | C95 | ✅ | ✅ | ✅ | |
| `intptr_t` | C99 | ✅ | ✅ | ✅ | |
| `uintptr_t` | C99 | ✅ | ✅ | ✅ | |

### 1.1.12 `<stdio.h>` (C89 部分)

| 接口/宏/类型 | glibc | musl | OHOS | 说明 |
|-------------|:-----:|:----:|:----:|------|
| `printf` | ✅ | ✅ | ✅ | |
| `fprintf` | ✅ | ✅ | ✅ | |
| `sprintf` | ✅ | ✅ | ✅ | |
| `sscanf` | ✅ | ✅ | ✅ | |
| `fscanf` | ✅ | ✅ | ✅ | |
| `scanf` | ✅ | ✅ | ✅ | |
| `fopen` | ✅ | ✅ | ✅ | |
| `fclose` | ✅ | ✅ | ✅ | |
| `fread` | ✅ | ✅ | ✅ | |
| `fwrite` | ✅ | ✅ | ✅ | |
| `fseek` | ✅ | ✅ | ✅ | |
| `ftell` | ✅ | ✅ | ✅ | |
| `rewind` | ✅ | ✅ | ✅ | |
| `fgetpos` | ✅ | ✅ | ✅ | |
| `fsetpos` | ✅ | ✅ | ✅ | |
| `feof` | ✅ | ✅ | ✅ | |
| `ferror` | ✅ | ✅ | ✅ | |
| `clearerr` | ✅ | ✅ | ✅ | |
| `fflush` | ✅ | ✅ | ✅ | |
| `fputc` | ✅ | ✅ | ✅ | |
| `fputs` | ✅ | ✅ | ✅ | |
| `putc` | ✅ | ✅ | ✅ | |
| `putchar` | ✅ | ✅ | ✅ | |
| `puts` | ✅ | ✅ | ✅ | |
| `ungetc` | ✅ | ✅ | ✅ | |
| `getc` | ✅ | ✅ | ✅ | |
| `getchar` | ✅ | ✅ | ✅ | |
| `fgets` | ✅ | ✅ | ✅ | |
| `gets` | ✅ | ✅ | ✅ | C11 移除, C23 移除 |
| `perror` | ✅ | ✅ | ✅ | |
| `remove` | ✅ | ✅ | ✅ | |
| `rename` | ✅ | ✅ | ✅ | |
| `tmpfile` | ✅ | ✅ | ✅ | |
| `tmpnam` | ✅ | ✅ | ✅ | |
| `fcloseall` | GNU | ✅ | ❌ | ❌ | musl 不支持 |
| `FILE` | ✅ | ✅ | ✅ | ⚠️ musl 不透明结构体 |
| `EOF` | ✅ | ✅ | ✅ | |
| `NULL` | ✅ | ✅ | ✅ | |
| `stdin` | ✅ | ✅ | ✅ | |
| `stdout` | ✅ | ✅ | ✅ | |
| `stderr` | ✅ | ✅ | ✅ | |
| `BUFSIZ` | ✅ | ✅ | ✅ | glibc: 8192; musl: 4096 |
| `FILENAME_MAX` | ✅ | ✅ | ✅ | |
| `FOPEN_MAX` | ✅ | ✅ | ✅ | |
| `L_tmpnam` | ✅ | ✅ | ✅ | |
| `SEEK_CUR` | ✅ | ✅ | ✅ | |
| `SEEK_END` | ✅ | ✅ | ✅ | |
| `SEEK_SET` | ✅ | ✅ | ✅ | |
| `_IOFBF` | ✅ | ✅ | ✅ | |
| `_IOLBF` | ✅ | ✅ | ✅ | |
| `_IONBF` | ✅ | ✅ | ✅ | |
| `setbuf` | ✅ | ✅ | ✅ | |
| `setvbuf` | ✅ | ✅ | ✅ | |
| `vprintf` | ✅ | ✅ | ✅ | |
| `vfprintf` | ✅ | ✅ | ✅ | |
| `vsprintf` | ✅ | ✅ | ✅ | |
| `snprintf` | C99 | ✅ | ✅ | ✅ | |
| `vsnprintf` | C99 | ✅ | ✅ | ✅ | |
| `vfscanf` | C99 | ✅ | ✅ | ✅ | |
| `vscanf` | C99 | ✅ | ✅ | ✅ | |
| `vsscanf` | C99 | ✅ | ✅ | ✅ | |
| `fwide` | C95 | ✅ | ✅ | ✅ | |
| `fwprintf` | C95 | ✅ | ✅ | ✅ | |
| `fwscanf` | C95 | ✅ | ✅ | ✅ | |
| `swprintf` | C95 | ✅ | ✅ | ✅ | |
| `wprintf` | C95 | ✅ | ✅ | ✅ | |
| `wscanf` | C95 | ✅ | ✅ | ✅ | |
| `fwscanf` | C95 | ✅ | ✅ | ✅ | |
| `swscanf` | C95 | ✅ | ✅ | ✅ | |
| `fgetwc` | C95 | ✅ | ✅ | ✅ | |
| `fgetws` | C95 | ✅ | ✅ | ✅ | |
| `fputwc` | C95 | ✅ | ✅ | ✅ | |
| `fputws` | C95 | ✅ | ✅ | ✅ | |
| `getwc` | C95 | ✅ | ✅ | ✅ | |
| `getwchar` | C95 | ✅ | ✅ | ✅ | |
| `putwc` | C95 | ✅ | ✅ | ✅ | |
| `putwchar` | C95 | ✅ | ✅ | ✅ | |
| `ungetwc` | C95 | ✅ | ✅ | ✅ | |

### 1.1.13 `<stdlib.h>` (C89 部分)

| 接口/宏/类型 | glibc | musl | OHOS | 说明 |
|-------------|:-----:|:----:|:----:|------|
| `malloc` | ✅ | ✅ | ✅ | musl 使用 mallocng 分配器 |
| `calloc` | ✅ | ✅ | ✅ | |
| `realloc` | ✅ | ✅ | ✅ | |
| `free` | ✅ | ✅ | ✅ | |
| `abort` | ✅ | ✅ | ✅ | |
| `atexit` | ✅ | ✅ | ✅ | |
| `at_quick_exit` | C11 | ✅ | ✅ | ✅ | |
| `exit` | ✅ | ✅ | ✅ | |
| `_Exit` | C99 | ✅ | ✅ | ✅ | |
| `quick_exit` | C11 | ✅ | ✅ | ✅ | |
| `atoi` | ✅ | ✅ | ✅ | |
| `atol` | ✅ | ✅ | ✅ | |
| `atof` | ✅ | ✅ | ✅ | |
| `strtol` | ✅ | ✅ | ✅ | |
| `strtoul` | ✅ | ✅ | ✅ | |
| `strtod` | ✅ | ✅ | ✅ | |
| `strtof` | C99 | ✅ | ✅ | ✅ | |
| `strtold` | C99 | ✅ | ✅ | ✅ | |
| `strtoll` | C99 | ✅ | ✅ | ✅ | |
| `strtoull` | C99 | ✅ | ✅ | ✅ | |
| `strtoimax` | C99 | ✅ | ✅ | ✅ | |
| `strtoumax` | C99 | ✅ | ✅ | ✅ | |
| `rand` | ✅ | ✅ | ✅ | |
| `srand` | ✅ | ✅ | ✅ | |
| `qsort` | ✅ | ✅ | ✅ | |
| `bsearch` | ✅ | ✅ | ✅ | |
| `abs` | ✅ | ✅ | ✅ | |
| `labs` | ✅ | ✅ | ✅ | |
| `llabs` | C99 | ✅ | ✅ | ✅ | |
| `div` | ✅ | ✅ | ✅ | |
| `ldiv` | ✅ | ✅ | ✅ | |
| `lldiv` | C99 | ✅ | ✅ | ✅ | |
| `mblen` | ✅ | ✅ | ✅ | |
| `mbtowc` | ✅ | ✅ | ✅ | |
| `wctomb` | ✅ | ✅ | ✅ | |
| `mbstowcs` | ✅ | ✅ | ✅ | |
| `wcstombs` | ✅ | ✅ | ✅ | |
| `getenv` | ✅ | ✅ | ✅ | |
| `system` | ✅ | ✅ | ✅ | ⚠️ musl 非线程安全 |
| `EXIT_SUCCESS` | ✅ | ✅ | ✅ | |
| `EXIT_FAILURE` | ✅ | ✅ | ✅ | |
| `RAND_MAX` | ✅ | ✅ | ✅ | |
| `MB_CUR_MAX` | ✅ | ✅ | ✅ | |
| `NULL` | ✅ | ✅ | ✅ | |
| `EXIT_FAILURE` | ✅ | ✅ | ✅ | |
| `div_t` | ✅ | ✅ | ✅ | |
| `ldiv_t` | ✅ | ✅ | ✅ | |
| `lldiv_t` | C99 | ✅ | ✅ | ✅ | |
| `ldiv_t` | ✅ | ✅ | ✅ | |
| `atoll` | C99 | ✅ | ✅ | ✅ | |
| `realpath` | POSIX | ✅ | ✅ | ✅ | musl 依赖 /proc |
| `mkstemp` | POSIX | ✅ | ✅ | ✅ | |
| `mkdtemp` | POSIX | ✅ | ✅ | ✅ | |
| `mkostemp` | GNU | ✅ | ✅ | ✅ | |
| `mkostemps` | GNU | ✅ | ✅ | ✅ | |
| `mkstemps` | GNU | ✅ | ✅ | ✅ | |
| `getopt` | POSIX | ✅ | ✅ | ✅ | ⚠️ 行为差异见后文 |
| `posix_memalign` | POSIX | ✅ | ✅ | ✅ | |
| `aligned_alloc` | C11 | ✅ | ✅ | ✅ | |
| `getloadavg` | GNU | ✅ | ❌ | ❌ | |
| `a64l` | POSIX | ✅ | ✅ | ✅ | |
| `l64a` | POSIX | ✅ | ✅ | ✅ | |
| `drand48` | POSIX | ✅ | ✅ | ✅ | |
| `erand48` | POSIX | ✅ | ✅ | ✅ | |
| `lrand48` | POSIX | ✅ | ✅ | ✅ | |
| `mrand48` | POSIX | ✅ | ✅ | ✅ | |
| `srand48` | POSIX | ✅ | ✅ | ✅ | |
| `seed48` | POSIX | ✅ | ✅ | ✅ | |
| `lcong48` | POSIX | ✅ | ✅ | ✅ | |
| `grantpt` | POSIX | ✅ | ✅ | ✅ | |
| `unlockpt` | POSIX | ✅ | ✅ | ✅ | |
| `ptsname` | POSIX | ✅ | ✅ | ✅ | |
| `getsubopt` | POSIX | ✅ | ✅ | ✅ | |
| `putenv` | POSIX | ✅ | ✅ | ✅ | |
| `setenv` | POSIX | ✅ | ✅ | ✅ | |
| `unsetenv` | POSIX | ✅ | ✅ | ✅ | |
| `clearenv` | POSIX | ✅ | ✅ | ✅ | |
| `getopt` | POSIX | ✅ | ✅ | ✅ | |

### 1.1.14 `<string.h>` (C89 部分)

| 接口 | glibc | musl | OHOS | 说明 |
|------|:-----:|:----:|:----:|------|
| `memcpy` | ✅ | ✅ | ✅ | |
| `memmove` | ✅ | ✅ | ✅ | |
| `memset` | ✅ | ✅ | ✅ | |
| `memcmp` | ✅ | ✅ | ✅ | |
| `memchr` | ✅ | ✅ | ✅ | |
| `strcpy` | ✅ | ✅ | ✅ | |
| `strncpy` | ✅ | ✅ | ✅ | |
| `strcat` | ✅ | ✅ | ✅ | |
| `strncat` | ✅ | ✅ | ✅ | |
| `strcmp` | ✅ | ✅ | ✅ | |
| `strncmp` | ✅ | ✅ | ✅ | |
| `strchr` | ✅ | ✅ | ✅ | |
| `strrchr` | ✅ | ✅ | ✅ | |
| `strstr` | ✅ | ✅ | ✅ | |
| `strlen` | ✅ | ✅ | ✅ | |
| `strtok` | ✅ | ✅ | ✅ | |
| `strerror` | ✅ | ✅ | ✅ | |
| `strerror_r` | POSIX | ✅ | ✅ | ✅ | glibc: GNU 版; musl: POSIX 版签名不同 |
| `strtok_r` | POSIX | ✅ | ✅ | ✅ | |
| `strdup` | POSIX | ✅ | ✅ | ✅ | |
| `strndup` | POSIX | ✅ | ✅ | ✅ | |
| `strspn` | ✅ | ✅ | ✅ | |
| `strcspn` | ✅ | ✅ | ✅ | |
| `strpbrk` | ✅ | ✅ | ✅ | |
| `memccpy` | POSIX | ✅ | ✅ | ✅ | |
| `mempcpy` | GNU | ✅ | ✅ | ✅ | |
| `memmem` | GNU | ✅ | ✅ | ✅ | |
| `strcasecmp` | POSIX | ✅ | ✅ | ✅ | |
| `strncasecmp` | POSIX | ✅ | ✅ | ✅ | |
| `strcasestr` | GNU | ✅ | ✅ | ✅ | |
| `strsep` | BSD | ✅ | ✅ | ✅ | |
| `stpcpy` | BSD | ✅ | ✅ | ✅ | |
| `stpncpy` | POSIX | ✅ | ✅ | ✅ | |
| `strsignal` | POSIX | ✅ | ✅ | ✅ | |
| `strverscmp` | GNU | ✅ | ✅ | ✅ | |
| `strchrnul` | GNU | ✅ | ✅ | ✅ | |
| `ffs` | POSIX | ✅ | ✅ | ✅ | |
| `ffsl` | POSIX | ✅ | ✅ | ✅ | |
| `ffsll` | POSIX | ✅ | ✅ | ✅ | |
| `rawmemchr` | GNU | ✅ | ❌ | ❌ | |
| `memfrob` | GNU | ✅ | ❌ | ❌ | |
| `basename` (GNU) | GNU | ✅ | ❌ | ❌ | musl 有 POSIX 版(libgen.h) |
| `strndupa` | GNU | ✅ | ❌ | ❌ | |
| `strdupa` | GNU | ✅ | ❌ | ❌ | |
| `explicit_bzero` | BSD | ✅ | ✅ | ✅ | |
| `strlcpy` | BSD | ✅ | ✅ | ✅ | |
| `strlcat` | BSD | ✅ | ✅ | ✅ | |
| `bcopy` | BSD | ✅ | ✅ | ✅ | 已废弃 |
| `bzero` | BSD | ✅ | ✅ | ✅ | 已废弃 |
| `bcmp` | BSD | ✅ | ✅ | ✅ | 已废弃 |
| `index` | BSD | ✅ | ✅ | ✅ | 已废弃 |
| `rindex` | BSD | ✅ | ✅ | ✅ | 已废弃 |

### 1.1.15 `<time.h>` (C89 部分)

| 接口/类型 | glibc | musl | OHOS | 说明 |
|-----------|:-----:|:----:|:----:|------|
| `time` | ✅ | ✅ | ✅ | |
| `clock` | ✅ | ✅ | ✅ | |
| `difftime` | ✅ | ✅ | ✅ | |
| `mktime` | ✅ | ✅ | ✅ | |
| `strftime` | ✅ | ✅ | ✅ | |
| `localtime` | ✅ | ✅ | ✅ | |
| `gmtime` | ✅ | ✅ | ✅ | |
| `asctime` | ✅ | ✅ | ✅ | |
| `ctime` | ✅ | ✅ | ✅ | |
| `localtime_r` | POSIX | ✅ | ✅ | ✅ | |
| `gmtime_r` | POSIX | ✅ | ✅ | ✅ | |
| `timegm` | POSIX | ✅ | ✅ | ✅ | |
| `clock_gettime` | POSIX | ✅ | ✅ | ✅ | |
| `clock_settime` | POSIX | ✅ | ✅ | ✅ | |
| `clock_getres` | POSIX | ✅ | ✅ | ✅ | |
| `asctime_r` | POSIX | ✅ | ✅ | ✅ | |
| `ctime_r` | POSIX | ✅ | ✅ | ✅ | |
| `strptime` | POSIX | ✅ | ✅ | ✅ | |
| `nanosleep` | POSIX | ✅ | ✅ | ✅ | |
| `timer_create` | POSIX | ✅ | ✅ | ✅ | |
| `timer_delete` | POSIX | ✅ | ✅ | ✅ | |
| `timer_gettime` | POSIX | ✅ | ✅ | ✅ | |
| `timer_settime` | POSIX | ✅ | ✅ | ✅ | |
| `timer_getoverrun` | POSIX | ✅ | ✅ | ✅ | |
| `time_t` | ✅ | ✅ | ✅ | musl 1.2.0+: 64-bit (含32位arch) |
| `clock_t` | ✅ | ✅ | ✅ | |
| `struct tm` | ✅ | ✅ | ✅ | |
| `CLOCKS_PER_SEC` | ✅ | ✅ | ✅ | |
| `struct timespec` | POSIX | ✅ | ✅ | ✅ | |
| `struct itimerspec` | POSIX | ✅ | ✅ | ✅ | |
| `CLOCK_REALTIME` | POSIX | ✅ | ✅ | ✅ | |
| `CLOCK_MONOTONIC` | POSIX | ✅ | ✅ | ✅ | |
| `CLOCK_PROCESS_CPUTIME_ID` | POSIX | ✅ | ✅ | ✅ | |
| `CLOCK_THREAD_CPUTIME_ID` | POSIX | ✅ | ✅ | ✅ | |
| `CLOCK_MONOTONIC_RAW` | Linux | ✅ | ✅ | ✅ | |
| `CLOCK_BOOTTIME` | Linux | ✅ | ✅ | ✅ | |
| `CLOCK_REALTIME_ALARM` | Linux | ✅ | ✅ | ✅ | |
| `CLOCK_BOOTTIME_ALARM` | Linux | ✅ | ✅ | ✅ | |
| `CLOCK_TAI` | Linux | ✅ | ✅ | ✅ | |
| `tzset` | POSIX | ✅ | ✅ | ✅ | |
| `tzname` | POSIX | ✅ | ✅ | ✅ | |
| `daylight` | POSIX | ✅ | ✅ | ✅ | |
| `timezone` | POSIX | ✅ | ✅ | ✅ | |
| `gettimeofday` | POSIX | ✅ | ✅ | ✅ | 已被 clock_gettime 替代 |
| `settimeofday` | POSIX | ✅ | ✅ | ✅ | |
| `gettimeofday` | POSIX | ✅ | ✅ | ✅ | |
| `adjtime` | POSIX | ✅ | ✅ | ✅ | |
| `clock_nanosleep` | POSIX | ✅ | ✅ | ✅ | |


---

## 1.2 C99 新增接口

### 1.2.1 `<complex.h>` — 全部复数函数

| 接口 | glibc | musl | OHOS | 说明 |
|------|:-----:|:----:|:----:|------|
| `cabs` | ✅ | ✅ | ✅ | |
| `cacos` | ✅ | ✅ | ✅ | |
| `cacosh` | ✅ | ✅ | ✅ | |
| `carg` | ✅ | ✅ | ✅ | |
| `casin` | ✅ | ✅ | ✅ | |
| `casinh` | ✅ | ✅ | ✅ | |
| `catan` | ✅ | ✅ | ✅ | |
| `catanh` | ✅ | ✅ | ✅ | |
| `ccos` | ✅ | ✅ | ✅ | |
| `ccosh` | ✅ | ✅ | ✅ | |
| `cexp` | ✅ | ✅ | ✅ | |
| `cimag` | ✅ | ✅ | ✅ | |
| `clog` | ✅ | ✅ | ✅ | |
| `clog10` | GNU | ✅ | ❌ | ❌ | |
| `conj` | ✅ | ✅ | ✅ | |
| `cpow` | ✅ | ✅ | ✅ | |
| `cproj` | ✅ | ✅ | ✅ | |
| `creal` | ✅ | ✅ | ✅ | |
| `csin` | ✅ | ✅ | ✅ | |
| `csinh` | ✅ | ✅ | ✅ | |
| `csqrt` | ✅ | ✅ | ✅ | |
| `ctan` | ✅ | ✅ | ✅ | |
| `ctanh` | ✅ | ✅ | ✅ | |
| `Complex`/`_Complex` | ✅ | ✅ | ✅ | |
| `I` (虚数单位) | ✅ | ✅ | ✅ | |
| `crealf` | ✅ | ✅ | ✅ | |
| `creall` | ✅ | ✅ | ✅ | |
| `cimagf` | ✅ | ✅ | ✅ | |
| `cimagl` | ✅ | ✅ | ✅ | |
| `cabsl` | ✅ | ✅ | ✅ | |

### 1.2.2 `<fenv.h>`

| 接口/类型 | glibc | musl | OHOS | 说明 |
|-----------|:-----:|:----:|:----:|------|
| `fenv_t` | ✅ | ✅ | ✅ | |
| `fexcept_t` | ✅ | ✅ | ✅ | |
| `feclearexcept` | ✅ | ✅ | ✅ | |
| `fegetexceptflag` | ✅ | ✅ | ✅ | |
| `feraiseexcept` | ✅ | ✅ | ✅ | |
| `fesetexceptflag` | ✅ | ✅ | ✅ | |
| `fetestexcept` | ✅ | ✅ | ✅ | |
| `fegetround` | ✅ | ✅ | ✅ | |
| `fesetround` | ✅ | ✅ | ✅ | |
| `fegetenv` | ✅ | ✅ | ✅ | |
| `feholdexcept` | ✅ | ✅ | ✅ | |
| `fesetenv` | ✅ | ✅ | ✅ | |
| `feupdateenv` | ✅ | ✅ | ✅ | |
| `FE_DIVBYZERO` | ✅ | ✅ | ✅ | |
| `FE_INEXACT` | ✅ | ✅ | ✅ | |
| `FE_INVALID` | ✅ | ✅ | ✅ | |
| `FE_OVERFLOW` | ✅ | ✅ | ✅ | |
| `FE_UNDERFLOW` | ✅ | ✅ | ✅ | |
| `FE_ALL_EXCEPT` | ✅ | ✅ | ✅ | |
| `FE_DOWNWARD` | ✅ | ✅ | ✅ | |
| `FE_TONEAREST` | ✅ | ✅ | ✅ | |
| `FE_TOWARDZERO` | ✅ | ✅ | ✅ | |
| `FE_UPWARD` | ✅ | ✅ | ✅ | |
| `FE_DFL_ENV` | ✅ | ✅ | ✅ | |
| `FE_NOMASK_ENV` | ✅ | ❌ | ❌ | musl 不支持（遵循严格浮点模型） |
| `feenableexcept` | GNU | ✅ | ❌ | ❌ | |
| `fedisableexcept` | GNU | ✅ | ❌ | ❌ | |
| `fegetexcept` | GNU | ✅ | ❌ | ❌ | |

### 1.2.3 `<inttypes.h>`

| 接口/宏 | glibc | musl | OHOS | 说明 |
|---------|:-----:|:----:|:----:|------|
| `PRId8`/`PRIi8` | ✅ | ✅ | ✅ | |
| `PRId16`/`PRIi16` | ✅ | ✅ | ✅ | |
| `PRId32`/`PRIi32` | ✅ | ✅ | ✅ | |
| `PRId64`/`PRIi64` | ✅ | ✅ | ✅ | |
| `PRIdLEAST8`/`PRIiLEAST8` | ✅ | ✅ | ✅ | |
| `PRIdLEAST16`/`PRIiLEAST16` | ✅ | ✅ | ✅ | |
| `PRIdLEAST32`/`PRIiLEAST32` | ✅ | ✅ | ✅ | |
| `PRIdLEAST64`/`PRIiLEAST64` | ✅ | ✅ | ✅ | |
| `PRIdFAST8`/`PRIiFAST8` | ✅ | ✅ | ✅ | |
| `PRIdFAST16`/`PRIiFAST16` | ✅ | ✅ | ✅ | |
| `PRIdFAST32`/`PRIiFAST32` | ✅ | ✅ | ✅ | |
| `PRIdFAST64`/`PRIiFAST64` | ✅ | ✅ | ✅ | |
| `PRIdMAX`/`PRIiMAX` | ✅ | ✅ | ✅ | |
| `PRIdPTR`/`PRIiPTR` | ✅ | ✅ | ✅ | |
| `PRIo8` | ✅ | ✅ | ✅ | |
| `PRIu8` | ✅ | ✅ | ✅ | |
| `PRIx8`/`PRIX8` | ✅ | ✅ | ✅ | |
| `PRIo16`/`PRIu16`/`PRIx16`/`PRIX16` | ✅ | ✅ | ✅ | |
| `PRIo32`/`PRIu32`/`PRIx32`/`PRIX32` | ✅ | ✅ | ✅ | |
| `PRIo64`/`PRIu64`/`PRIx64`/`PRIX64` | ✅ | ✅ | ✅ | |
| `PRIoMAX`/`PRIuMAX`/`PRIxMAX`/`PRIXMAX` | ✅ | ✅ | ✅ | |
| `SCNd8`/`SCNi8` | ✅ | ✅ | ✅ | |
| `SCNd16`/`SCNi16` | ✅ | ✅ | ✅ | |
| `SCNd32`/`SCNi32` | ✅ | ✅ | ✅ | |
| `SCNd64`/`SCNi64` | ✅ | ✅ | ✅ | |
| `SCNo8`/`SCNu8`/`SCNx8` | ✅ | ✅ | ✅ | |
| `SCNo16`/`SCNu16`/`SCNx16` | ✅ | ✅ | ✅ | |
| `SCNo32`/`SCNu32`/`SCNx32` | ✅ | ✅ | ✅ | |
| `SCNo64`/`SCNu64`/`SCNx64` | ✅ | ✅ | ✅ | |
| `SCNoMAX`/`SCNuMAX`/`SCNxMAX` | ✅ | ✅ | ✅ | |
| `strtoimax` | ✅ | ✅ | ✅ | |
| `strtoumax` | ✅ | ✅ | ✅ | |
| `imaxabs` | ✅ | ✅ | ✅ | |
| `imaxdiv` | ✅ | ✅ | ✅ | |
| `strtoimax` | ✅ | ✅ | ✅ | |
| `strtoumax` | ✅ | ✅ | ✅ | |
| `intmax_t` | ✅ | ✅ | ✅ | |
| `uintmax_t` | ✅ | ✅ | ✅ | |
| `imaxdiv_t` | ✅ | ✅ | ✅ | |

### 1.2.4 `<stdbool.h>`

| 接口/宏 | glibc | musl | OHOS | 说明 |
|---------|:-----:|:----:|:----:|------|
| `bool` | ✅ | ✅ | ✅ | 展开为 _Bool |
| `true` | ✅ | ✅ | ✅ | 展开为 1 |
| `false` | ✅ | ✅ | ✅ | 展开为 0 |
| `__bool_true_false_are_defined` | ✅ | ✅ | ✅ | |

### 1.2.5 `<stdint.h>`

| 接口/类型 | glibc | musl | OHOS | 说明 |
|-----------|:-----:|:----:|:----:|------|
| `int8_t` | ✅ | ✅ | ✅ | |
| `int16_t` | ✅ | ✅ | ✅ | |
| `int32_t` | ✅ | ✅ | ✅ | |
| `int64_t` | ✅ | ✅ | ✅ | |
| `uint8_t` | ✅ | ✅ | ✅ | |
| `uint16_t` | ✅ | ✅ | ✅ | |
| `uint32_t` | ✅ | ✅ | ✅ | |
| `uint64_t` | ✅ | ✅ | ✅ | |
| `int_least8_t` ~ `int_least64_t` | ✅ | ✅ | ✅ | |
| `uint_least8_t` ~ `uint_least64_t` | ✅ | ✅ | ✅ | |
| `int_fast8_t` ~ `int_fast64_t` | ✅ | ✅ | ✅ | |
| `uint_fast8_t` ~ `uint_fast64_t` | ✅ | ✅ | ✅ | |
| `intptr_t` | ✅ | ✅ | ✅ | |
| `uintptr_t` | ✅ | ✅ | ✅ | |
| `intmax_t` | ✅ | ✅ | ✅ | |
| `uintmax_t` | ✅ | ✅ | ✅ | |
| `INT8_MIN`/`INT8_MAX` | ✅ | ✅ | ✅ | |
| `INT16_MIN`/`INT16_MAX` | ✅ | ✅ | ✅ | |
| `INT32_MIN`/`INT32_MAX` | ✅ | ✅ | ✅ | |
| `INT64_MIN`/`INT64_MAX` | ✅ | ✅ | ✅ | |
| `UINT8_MAX` ~ `UINT64_MAX` | ✅ | ✅ | ✅ | |
| `INT_LEAST8_MIN` ~ `INT_LEAST64_MAX` | ✅ | ✅ | ✅ | |
| `UINT_LEAST8_MAX` ~ `UINT_LEAST64_MAX` | ✅ | ✅ | ✅ | |
| `INT_FAST8_MIN` ~ `INT_FAST64_MAX` | ✅ | ✅ | ✅ | |
| `UINT_FAST8_MAX` ~ `UINT_FAST64_MAX` | ✅ | ✅ | ✅ | |
| `INTPTR_MIN`/`INTPTR_MAX` | ✅ | ✅ | ✅ | |
| `UINTPTR_MAX` | ✅ | ✅ | ✅ | |
| `INTMAX_MIN`/`INTMAX_MAX` | ✅ | ✅ | ✅ | |
| `UINTMAX_MAX` | ✅ | ✅ | ✅ | |
| `SIZE_MAX` | ✅ | ✅ | ✅ | |
| `PTRDIFF_MAX` | ✅ | ✅ | ✅ | |
| `PTRDIFF_MIN` | ✅ | ✅ | ✅ | |
| `INT8_C`/`INT16_C`/`INT32_C`/`INT64_C` | ✅ | ✅ | ✅ | |
| `UINT8_C`/`UINT16_C`/`UINT32_C`/`UINT64_C` | ✅ | ✅ | ✅ | |
| `INTMAX_C` | ✅ | ✅ | ✅ | |
| `UINTMAX_C` | ✅ | ✅ | ✅ | |

### 1.2.6 `<tgmath.h>`

| 接口 | glibc | musl | OHOS | 说明 |
|------|:-----:|:----:|:----:|------|
| `acos` (泛型) | ✅ | ✅ | ✅ | |
| `asin` (泛型) | ✅ | ✅ | ✅ | |
| `atan` (泛型) | ✅ | ✅ | ✅ | |
| `atan2` (泛型) | ✅ | ✅ | ✅ | |
| `ceil` (泛型) | ✅ | ✅ | ✅ | |
| `cos` (泛型) | ✅ | ✅ | ✅ | |
| `exp` (泛型) | ✅ | ✅ | ✅ | |
| `floor` (泛型) | ✅ | ✅ | ✅ | |
| `log` (泛型) | ✅ | ✅ | ✅ | |
| `pow` (泛型) | ✅ | ✅ | ✅ | |
| `sin` (泛型) | ✅ | ✅ | ✅ | |
| `sqrt` (泛型) | ✅ | ✅ | ✅ | |
| `tan` (泛型) | ✅ | ✅ | ✅ | |
| `acosh` ~ `tanh` (泛型) | ✅ | ✅ | ✅ | |
| `cabs` (泛型) | ✅ | ✅ | ✅ | |
| `carg` (泛型) | ✅ | ✅ | ✅ | |
| `cimag` (泛型) | ✅ | ✅ | ✅ | |
| `conj` (泛型) | ✅ | ✅ | ✅ | |
| `creal` (泛型) | ✅ | ✅ | ✅ | |
| `cexp` (泛型) | ✅ | ✅ | ✅ | |
| `clog` (泛型) | ✅ | ✅ | ✅ | |
| `csqrt` (泛型) | ✅ | ✅ | ✅ | |
| `fabs` (泛型) | ✅ | ✅ | ✅ | |
| `fma` (泛型) | ✅ | ✅ | ✅ | |
| `fmax` (泛型) | ✅ | ✅ | ✅ | |
| `fmin` (泛型) | ✅ | ✅ | ✅ | |
| 所有其他 C99 泛型宏 | ✅ | ✅ | ✅ | |

---

## 1.3 C11 新增接口

### 1.3.1 `<stdalign.h>`

| 接口/宏 | glibc | musl | OHOS | 说明 |
|---------|:-----:|:----:|:----:|------|
| `alignas` | ✅ | ✅ | ✅ | 展开为 _Alignas |
| `alignof` | ✅ | ✅ | ✅ | 展开为 _Alignof |
| `__alignas_is_defined` | ✅ | ✅ | ✅ | |
| `__alignof_is_defined` | ✅ | ✅ | ✅ | |

### 1.3.2 `<stdnoreturn.h>`

| 接口/宏 | glibc | musl | OHOS | 说明 |
|---------|:-----:|:----:|:----:|------|
| `noreturn` | ✅ | ✅ | ✅ | 展开为 _Noreturn |

### 1.3.3 `<threads.h>` (C11 线程)

| 接口/类型 | glibc | musl | OHOS | 说明 |
|-----------|:-----:|:----:|:----:|------|
| `thrd_create` | ✅ | ✅ | ✅ | musl 基于 pthread 实现 |
| `thrd_join` | ✅ | ✅ | ✅ | |
| `thrd_detach` | ✅ | ✅ | ✅ | |
| `thrd_exit` | ✅ | ✅ | ✅ | |
| `thrd_sleep` | ✅ | ✅ | ✅ | |
| `thrd_yield` | ✅ | ✅ | ✅ | |
| `thrd_equal` | ✅ | ✅ | ✅ | |
| `thrd_current` | ✅ | ✅ | ✅ | |
| `mtx_init` | ✅ | ✅ | ✅ | |
| `mtx_lock` | ✅ | ✅ | ✅ | |
| `mtx_timedlock` | ✅ | ✅ | ✅ | |
| `mtx_trylock` | ✅ | ✅ | ✅ | |
| `mtx_unlock` | ✅ | ✅ | ✅ | |
| `mtx_destroy` | ✅ | ✅ | ✅ | |
| `mtx_plain` | ✅ | ✅ | ✅ | |
| `mtx_recursive` | ✅ | ✅ | ✅ | |
| `mtx_timed` | ✅ | ✅ | ✅ | |
| `cnd_init` | ✅ | ✅ | ✅ | |
| `cnd_signal` | ✅ | ✅ | ✅ | |
| `cnd_broadcast` | ✅ | ✅ | ✅ | |
| `cnd_wait` | ✅ | ✅ | ✅ | |
| `cnd_timedwait` | ✅ | ✅ | ✅ | |
| `cnd_destroy` | ✅ | ✅ | ✅ | |
| `tss_create` | ✅ | ✅ | ✅ | |
| `tss_get` | ✅ | ✅ | ✅ | |
| `tss_set` | ✅ | ✅ | ✅ | |
| `tss_delete` | ✅ | ✅ | ✅ | |
| `call_once` | ✅ | ✅ | ✅ | |
| `ONCE_FLAG_INIT` | ✅ | ✅ | ✅ | |
| `TSS_DTOR_ITERATIONS` | ✅ | ✅ | ✅ | |
| `thread_local` | ✅ | ✅ | ✅ | |
| `thrd_t` | ✅ | ✅ | ✅ | |
| `mtx_t` | ✅ | ✅ | ✅ | |
| `cnd_t` | ✅ | ✅ | ✅ | |
| `tss_t` | ✅ | ✅ | ✅ | |
| `tss_dtor_t` | ✅ | ✅ | ✅ | |
| `once_flag` | ✅ | ✅ | ✅ | |

### 1.3.4 `<uchar.h>` (C11 Unicode)

| 接口/类型 | glibc | musl | OHOS | 说明 |
|-----------|:-----:|:----:|:----:|------|
| `char16_t` | ✅ | ✅ | ✅ | |
| `char32_t` | ✅ | ✅ | ✅ | |
| `mbrtoc16` | ✅ | ✅ | ✅ | |
| `mbrtoc32` | ✅ | ✅ | ✅ | |
| `c16rtomb` | ✅ | ✅ | ✅ | |
| `c32rtomb` | ✅ | ✅ | ✅ | |
| `mbstate_t` | ✅ | ✅ | ✅ | |

### 1.3.5 C11 语言关键字

| 关键字 | glibc | musl | OHOS | 说明 |
|--------|:-----:|:----:|:----:|------|
| `_Alignas` | ✅ | ✅ | ✅ | |
| `_Alignof` | ✅ | ✅ | ✅ | |
| `_Atomic` | ✅ | ✅ | ✅ | |
| `_Generic` | ✅ | ✅ | ✅ | |
| `_Noreturn` | ✅ | ✅ | ✅ | |
| `_Static_assert` | ✅ | ✅ | ✅ | |
| `_Thread_local` | ✅ | ✅ | ✅ | |

---

## 1.4 C17/C23 新增接口

| 接口 | 标准 | glibc | musl | OHOS | 说明 |
|------|------|:-----:|:----:|:----:|------|
| `memset_s` | C11.K/ISO | ✅ | ✅ | ✅ | 安全内存填充 |
| `gets_s` | C11.K | ✅ | ❌ | ❌ | musl 不实现此函数 |
| `mbstowcs_s` | C11.K | ✅ | ❌ | ❌ | |
| `wcstombs_s` | C11.K | ✅ | ❌ | ❌ | |
| `ungetc_s` | C23 | ⚠️ | ❌ | ❌ | glibc 部分支持 |
| `memset_explicit` | C23 | ⚠️ | ❌ | ❌ | glibc 部分 |
| `bit_ceil` | C23 | ✅ | ⚠️ | ⚠️ | musl 可能未跟进 |
| `bit_floor` | C23 | ✅ | ⚠️ | ⚠️ | |
| `bit_width` | C23 | ✅ | ⚠️ | ⚠️ | |
| `count_ones` | C23 | ✅ | ⚠️ | ⚠️ | |
| `count_zeros` | C23 | ✅ | ⚠️ | ⚠️ | |
| `has_single_bit` | C23 | ✅ | ⚠️ | ⚠️ | |
| `bit_cast` | C23 | ✅ | ⚠️ | ⚠️ | |
| `calloc_sized` | C23 | ⚠️ | ❌ | ❌ | |
| `realloc_sized` | C23 | ⚠️ | ❌ | ❌ | |
| `memcpy_s` | C11.K | ✅ | ❌ | ❌ | |
| `memmove_s` | C11.K | ✅ | ❌ | ❌ | |
| `strcpy_s` | C11.K | ✅ | ❌ | ❌ | |
| `strncpy_s` | C11.K | ✅ | ❌ | ❌ | |
| `strcat_s` | C11.K | ✅ | ❌ | ❌ | |
| `strncat_s` | C11.K | ✅ | ❌ | ❌ | |
| `strtok_s` | C11.K | ✅ | ❌ | ❌ | |
| `asctime_s` | C11.K | ✅ | ❌ | ❌ | |
| `ctime_s` | C11.K | ✅ | ❌ | ❌ | |
| `printf_s`/`fprintf_s` | C11.K | ✅ | ❌ | ❌ | |
| `scanf_s`/`fscanf_s` | C11.K | ✅ | ❌ | ❌ | |
| `sprintf_s`/`snprintf_s` | C11.K | ✅ | ❌ | ❌ | |
| `sscanf_s` | C11.K | ✅ | ❌ | ❌ | |
| `fopen_s` | C11.K | ✅ | ❌ | ❌ | |
| `freopen_s` | C11.K | ✅ | ❌ | ❌ | |
| `tmpfile_s` | C11.K | ✅ | ❌ | ❌ | |
| `gmtime_s` | C11.K | ✅ | ❌ | ❌ | |
| `localtime_s` | C11.K | ✅ | ⚠️ | ⚠️ | 签名不同! 见开发者影响分析 |
| `qsort_s` | C11.K | ✅ | ⚠️ | ⚠️ | 签名不同! |
| `bsearch_s` | C11.K | ✅ | ⚠️ | ⚠️ | 签名不同! |

> **关键差异**: C11 Annex K (`_s` 后缀安全函数) 是 glibc 独有实现，musl 明确拒绝实现。musl 认为 C11 Annex K 不是真正的 C 标准（ISO 仅有参考性 Annex），且这些函数设计有缺陷。


---

## 第二部分：POSIX 标准接口全量对比

### 总览

| POSIX 版本 | glibc 覆盖 | musl 覆盖 | OHOS musl 覆盖 | 说明 |
|------------|:----------:|:---------:|:--------------:|------|
| POSIX.1-2001 Base | ~100% | ~98% | ~98% | |
| POSIX.1-2008 Base | ~100% | ~97% | ~97% | |
| POSIX.1-2008 Options | ~95% | ~85% | ~90% | OHOS 增强了部分 |
| POSIX.1-2024 | ~90% | ~85% | ~85% | |

---

## 2.1 POSIX 文件与目录操作

### `<dirent.h>`

| 接口 | POSIX | glibc | musl | OHOS | 说明 |
|------|:-----:|:-----:|:----:|:----:|------|
| `opendir` | ✅ | ✅ | ✅ | ✅ | |
| `fdopendir` | 2008 | ✅ | ✅ | ✅ | |
| `readdir` | ✅ | ✅ | ✅ | ✅ | |
| `readdir_r` | 2008 | ✅ | ✅ | ✅ | POSIX.1-2008 标记为弃用 |
| `rewinddir` | ✅ | ✅ | ✅ | ✅ | |
| `seekdir` | ✅ | ✅ | ✅ | ✅ | |
| `telldir` | ✅ | ✅ | ✅ | ✅ | |
| `closedir` | ✅ | ✅ | ✅ | ✅ | |
| `DIR` | ✅ | ✅ | ✅ | ✅ | |
| `struct dirent` | ✅ | ✅ | ✅ | ✅ | |
| `ino_t` | ✅ | ✅ | ✅ | ✅ | |
| `off_t` | ✅ | ✅ | ✅ | ✅ | musl 始终 64-bit |
| `dirent.d_name` | ✅ | ✅ | ✅ | ✅ | |
| `dirent.d_ino` | ✅ | ✅ | ✅ | ✅ | |
| `dirent.d_type` | GNU | ✅ | ✅ | ✅ | |
| `DT_*` 常量 | GNU | ✅ | ✅ | ✅ | |
| `scandir` | POSIX | ✅ | ✅ | ✅ | |
| `alphasort` | POSIX | ✅ | ✅ | ✅ | |
| `versionsort` | GNU | ✅ | ✅ | ✅ | |

### `<fcntl.h>`

| 接口/宏 | glibc | musl | OHOS | 说明 |
|---------|:-----:|:----:|:----:|------|
| `open` | ✅ | ✅ | ✅ | |
| `openat` | ✅ | ✅ | ✅ | |
| `creat` | ✅ | ✅ | ✅ | |
| `fcntl` | ✅ | ✅ | ✅ | |
| `close` | ✅ | ✅ | ✅ | |
| `dup` | ✅ | ✅ | ✅ | |
| `dup2` | ✅ | ✅ | ✅ | |
| `dup3` | Linux | ✅ | ✅ | ✅ | |
| `closefrom` | Linux | ✅ | ✅ | ✅ | musl 1.2.6+ |
| `close_range` | Linux | ✅ | ✅ | ✅ | |
| `lseek` | ✅ | ✅ | ✅ | |
| `read` | ✅ | ✅ | ✅ | |
| `write` | ✅ | ✅ | ✅ | |
| `readv` | ✅ | ✅ | ✅ | |
| `writev` | ✅ | ✅ | ✅ | |
| `pread` | ✅ | ✅ | ✅ | |
| `pwrite` | ✅ | ✅ | ✅ | |
| `preadv` | ✅ | ✅ | ✅ | |
| `pwritev` | ✅ | ✅ | ✅ | |
| `preadv2` | Linux | ✅ | ✅ | ✅ | musl 1.2.5+ |
| `pwritev2` | Linux | ✅ | ✅ | ✅ | musl 1.2.5+ |
| `pipe` | ✅ | ✅ | ✅ | |
| `pipe2` | Linux | ✅ | ✅ | ✅ | |
| `O_RDONLY` | ✅ | ✅ | ✅ | |
| `O_WRONLY` | ✅ | ✅ | ✅ | |
| `O_RDWR` | ✅ | ✅ | ✅ | |
| `O_CREAT` | ✅ | ✅ | ✅ | |
| `O_EXCL` | ✅ | ✅ | ✅ | |
| `O_TRUNC` | ✅ | ✅ | ✅ | |
| `O_APPEND` | ✅ | ✅ | ✅ | |
| `O_NONBLOCK` | ✅ | ✅ | ✅ | |
| `O_CLOEXEC` | ✅ | ✅ | ✅ | |
| `O_NOCTTY` | ✅ | ✅ | ✅ | |
| `O_DIRECTORY` | ✅ | ✅ | ✅ | |
| `O_NOFOLLOW` | ✅ | ✅ | ✅ | |
| `O_SYNC` | ✅ | ✅ | ✅ | |
| `O_DSYNC` | ✅ | ✅ | ✅ | |
| `O_RSYNC` | ✅ | ✅ | ✅ | |
| `O_TMPFILE` | Linux | ✅ | ✅ | ✅ | |
| `O_PATH` | Linux | ✅ | ✅ | ✅ | |
| `O_DIRECT` | Linux | ✅ | ✅ | ✅ | |
| `F_DUPFD` | ✅ | ✅ | ✅ | |
| `F_DUPFD_CLOEXEC` | ✅ | ✅ | ✅ | |
| `F_GETFD` | ✅ | ✅ | ✅ | |
| `F_SETFD` | ✅ | ✅ | ✅ | |
| `FD_CLOEXEC` | ✅ | ✅ | ✅ | |
| `F_GETFL` | ✅ | ✅ | ✅ | |
| `F_SETFL` | ✅ | ✅ | ✅ | |
| `F_GETLK` | ✅ | ✅ | ✅ | |
| `F_SETLK` | ✅ | ✅ | ✅ | |
| `F_SETLKW` | ✅ | ✅ | ✅ | |
| `F_GETOWN` | ✅ | ✅ | ✅ | |
| `F_SETOWN` | ✅ | ✅ | ✅ | |
| `F_GETOWN_EX` | Linux | ✅ | ✅ | ✅ | |
| `F_SETOWN_EX` | Linux | ✅ | ✅ | ✅ | |
| `F_GETSIG` | ✅ | ✅ | ✅ | |
| `F_SETSIG` | ✅ | ✅ | ✅ | |
| `F_GETLEASE` | Linux | ✅ | ✅ | ✅ | |
| `F_SETLEASE` | Linux | ✅ | ✅ | ✅ | |
| `F_NOTIFY` | Linux | ✅ | ✅ | ✅ | |
| `F_GETPIPE_SZ` | Linux | ✅ | ✅ | ✅ | |
| `F_SETPIPE_SZ` | Linux | ✅ | ✅ | ✅ | |
| `F_ADD_SEALS` | Linux | ✅ | ✅ | ✅ | |
| `F_GET_SEALS` | Linux | ✅ | ✅ | ✅ | |
| `F_SEAL_SEAL` | Linux | ✅ | ✅ | ✅ | |
| `F_SEAL_SHRINK` | Linux | ✅ | ✅ | ✅ | |
| `F_SEAL_GROW` | Linux | ✅ | ✅ | ✅ | |
| `F_SEAL_WRITE` | Linux | ✅ | ✅ | ✅ | |
| `F_GET_RW_HINT` | Linux | ✅ | ✅ | ✅ | |
| `F_SET_RW_HINT` | Linux | ✅ | ✅ | ✅ | |
| `F_GET_FILE_RW_HINT` | Linux | ✅ | ✅ | ✅ | |
| `F_SET_FILE_RW_HINT` | Linux | ✅ | ✅ | ✅ | |
| `F_OFD_GETLK` | Linux | ✅ | ✅ | ✅ | |
| `F_OFD_SETLK` | Linux | ✅ | ✅ | ✅ | |
| `F_OFD_SETLKW` | Linux | ✅ | ✅ | ✅ | |
| `AT_FDCWD` | ✅ | ✅ | ✅ | |
| `AT_SYMLINK_NOFOLLOW` | ✅ | ✅ | ✅ | |
| `AT_REMOVEDIR` | ✅ | ✅ | ✅ | |
| `AT_SYMLINK_FOLLOW` | ✅ | ✅ | ✅ | |
| `AT_EACCESS` | ✅ | ✅ | ✅ | |
| `AT_EMPTY_PATH` | Linux | ✅ | ✅ | ✅ | |
| `AT_NO_AUTOMOUNT` | Linux | ✅ | ✅ | ✅ | |
| `AT_STATX_DONT_SYNC` | Linux | ✅ | ✅ | ✅ | |
| `AT_RECURSIVE` | Linux | ✅ | ✅ | ✅ | |
| `struct flock` | ✅ | ✅ | ✅ | |
| `struct flock64` | ✅ | ✅ | ✅ | |
| `POSIX_FADV_NORMAL` | ✅ | ✅ | ✅ | |
| `POSIX_FADV_SEQUENTIAL` | ✅ | ✅ | ✅ | |
| `POSIX_FADV_RANDOM` | ✅ | ✅ | ✅ | |
| `POSIX_FADV_WILLNEED` | ✅ | ✅ | ✅ | |
| `POSIX_FADV_DONTNEED` | ✅ | ✅ | ✅ | |
| `POSIX_FADV_NOREUSE` | ✅ | ✅ | ✅ | |
| `posix_fadvise` | ✅ | ✅ | ✅ | |
| `posix_fallocate` | ✅ | ✅ | ✅ | |
| `fallocate` | Linux | ✅ | ✅ | ✅ | |
| `sync_file_range` | Linux | ✅ | ✅ | ✅ | |
| `readahead` | Linux | ✅ | ✅ | ✅ | |
| `splice` | Linux | ✅ | ✅ | ✅ | |
| `tee` | Linux | ✅ | ✅ | ✅ | |
| `vmsplice` | Linux | ✅ | ✅ | ✅ | |
| `sendfile` | ✅ | ✅ | ✅ | |
| `FIONREAD` | ✅ | ✅ | ✅ | |
| `FIONBIO` | ✅ | ✅ | ✅ | |
| `FIOCLEX` | ✅ | ✅ | ✅ | |
| `FIONCLEX` | ✅ | ✅ | ✅ | |
| `name_to_handle_at` | Linux | ✅ | ✅ | ✅ | |
| `open_by_handle_at` | Linux | ✅ | ✅ | ✅ | |
| `struct file_handle` | Linux | ✅ | ✅ | ✅ | |

### `<sys/stat.h>`

| 接口/宏 | glibc | musl | OHOS | 说明 |
|---------|:-----:|:----:|:----:|------|
| `stat` | ✅ | ✅ | ✅ | |
| `fstat` | ✅ | ✅ | ✅ | |
| `lstat` | ✅ | ✅ | ✅ | |
| `fstatat` | ✅ | ✅ | ✅ | |
| `chmod` | ✅ | ✅ | ✅ | |
| `fchmod` | ✅ | ✅ | ✅ | |
| `fchmodat` | ✅ | ✅ | ✅ | |
| `chown` | ✅ | ✅ | ✅ | |
| `lchown` | ✅ | ✅ | ✅ | |
| `fchown` | ✅ | ✅ | ✅ | |
| `fchownat` | ✅ | ✅ | ✅ | |
| `umask` | ✅ | ✅ | ✅ | |
| `mkdir` | ✅ | ✅ | ✅ | |
| `mkdirat` | ✅ | ✅ | ✅ | |
| `mkfifo` | ✅ | ✅ | ✅ | |
| `mkfifoat` | ✅ | ✅ | ✅ | |
| `mknod` | ✅ | ✅ | ✅ | |
| `mknodat` | ✅ | ✅ | ✅ | |
| `statx` | Linux | ✅ | ✅ | ✅ | musl 1.2.5+ |
| `fstatat64` | 32-bit | ✅ | ✅ | ✅ | |
| `S_ISREG` | ✅ | ✅ | ✅ | |
| `S_ISDIR` | ✅ | ✅ | ✅ | |
| `S_ISCHR` | ✅ | ✅ | ✅ | |
| `S_ISBLK` | ✅ | ✅ | ✅ | |
| `S_ISFIFO` | ✅ | ✅ | ✅ | |
| `S_ISLNK` | ✅ | ✅ | ✅ | |
| `S_ISSOCK` | ✅ | ✅ | ✅ | |
| `S_TYPEISMQ` | XSI | ✅ | ❌ | ❌ | |
| `S_TYPEISSEM` | XSI | ✅ | ❌ | ❌ | |
| `S_TYPEISSHM` | XSI | ✅ | ❌ | ❌ | |
| `S_ISUID` | ✅ | ✅ | ✅ | |
| `S_ISGID` | ✅ | ✅ | ✅ | |
| `S_ISVTX` | ✅ | ✅ | ✅ | |
| `struct stat` | ✅ | ✅ | ✅ | ⚠️ 成员排列可能有差异 |
| `st_mode` | ✅ | ✅ | ✅ | |
| `st_ino` | ✅ | ✅ | ✅ | |
| `st_dev` | ✅ | ✅ | ✅ | |
| `st_nlink` | ✅ | ✅ | ✅ | |
| `st_uid` | ✅ | ✅ | ✅ | |
| `st_gid` | ✅ | ✅ | ✅ | |
| `st_size` | ✅ | ✅ | ✅ | |
| `st_atim` | ✅ | ✅ | ✅ | |
| `st_mtim` | ✅ | ✅ | ✅ | |
| `st_ctim` | ✅ | ✅ | ✅ | |
| `st_blksize` | ✅ | ✅ | ✅ | |
| `st_blocks` | ✅ | ✅ | ✅ | |
| `st_rdev` | ✅ | ✅ | ✅ | |
| `utimensat` | ✅ | ✅ | ✅ | |
| `futimens` | ✅ | ✅ | ✅ | |
| `futimes` | BSD | ✅ | ✅ | ✅ | |
| `lutimes` | BSD | ✅ | ✅ | ✅ | |
| `lchmod` | BSD | ✅ | ✅ | ✅ | |

### `<unistd.h>` (完整接口列表)

| 接口/宏 | glibc | musl | OHOS | 说明 |
|---------|:-----:|:----:|:----:|------|
| `access` | ✅ | ✅ | ✅ | |
| `faccessat` | ✅ | ✅ | ✅ | |
| `faccessat2` | Linux | ✅ | ✅ | ✅ | |
| `alarm` | ✅ | ✅ | ✅ | |
| `brk` | ✅ | ✅ | ✅ | |
| `sbrk` | ✅ | ✅ | ✅ | ⚠️ 仅兼容 |
| `chdir` | ✅ | ✅ | ✅ | |
| `fchdir` | ✅ | ✅ | ✅ | |
| `chown` | ✅ | ✅ | ✅ | |
| `lchown` | ✅ | ✅ | ✅ | |
| `fchown` | ✅ | ✅ | ✅ | |
| `chroot` | ✅ | ✅ | ✅ | |
| `close` | ✅ | ✅ | ✅ | |
| `dup` | ✅ | ✅ | ✅ | |
| `dup2` | ✅ | ✅ | ✅ | |
| `dup3` | ✅ | ✅ | ✅ | |
| `execve` | ✅ | ✅ | ✅ | |
| `execl` | ✅ | ✅ | ✅ | |
| `execle` | ✅ | ✅ | ✅ | |
| `execlp` | ✅ | ✅ | ✅ | |
| `execv` | ✅ | ✅ | ✅ | |
| `execvp` | ✅ | ✅ | ✅ | |
| `execvpe` | ✅ | ✅ | ✅ | |
| `fchownat` | ✅ | ✅ | ✅ | |
| `fdatasync` | ✅ | ✅ | ✅ | |
| `fork` | ✅ | ✅ | ✅ | |
| `_Fork` | 2024 | ✅ | ✅ | ✅ | musl 1.2.2+ |
| `fpathconf` | ✅ | ✅ | ✅ | |
| `fsync` | ✅ | ✅ | ✅ | |
| `ftruncate` | ✅ | ✅ | ✅ | |
| `getcwd` | ✅ | ✅ | ✅ | |
| `get_current_dir_name` | GNU | ✅ | ✅ | ✅ | |
| `getauxval` | ✅ | ✅ | ✅ | |
| `getegid` | ✅ | ✅ | ✅ | |
| `geteuid` | ✅ | ✅ | ✅ | |
| `getgid` | ✅ | ✅ | ✅ | |
| `getgroups` | ✅ | ✅ | ✅ | |
| `gethostid` | XSI | ✅ | ✅ | ✅ | |
| `gethostname` | ✅ | ✅ | ✅ | |
| `getlogin` | ✅ | ✅ | ✅ | |
| `getlogin_r` | ✅ | ✅ | ✅ | |
| `getopt` | ✅ | ✅ | ✅ | ⚠️ 行为差异 |
| `getopt_long` | GNU | ✅ | ✅ | ✅ | |
| `getopt_long_only` | GNU | ✅ | ✅ | ✅ | |
| `getpagesize` | BSD | ✅ | ✅ | ✅ | |
| `getpgid` | ✅ | ✅ | ✅ | |
| `getpgrp` | ✅ | ✅ | ✅ | |
| `getpid` | ✅ | ✅ | ✅ | |
| `getppid` | ✅ | ✅ | ✅ | |
| `getpriority` | ✅ | ✅ | ✅ | |
| `getrandom` | Linux | ✅ | ✅ | ✅ | |
| `getresgid` | ✅ | ✅ | ✅ | |
| `getresuid` | ✅ | ✅ | ✅ | |
| `getrlimit` | ✅ | ✅ | ✅ | |
| `getrusage` | ✅ | ✅ | ✅ | |
| `getsid` | ✅ | ✅ | ✅ | |
| `gettid` | Linux | ✅ | ✅ | ✅ | musl 1.2.2+ |
| `getuid` | ✅ | ✅ | ✅ | |
| `getwd` | LEGACY | ✅ | ✅ | ✅ | 已废弃 |
| `initgroups` | ✅ | ✅ | ✅ | |
| `ioctl` | ✅ | ✅ | ✅ | |
| `isatty` | ✅ | ✅ | ✅ | |
| `lchown` | ✅ | ✅ | ✅ | |
| `link` | ✅ | ✅ | ✅ | |
| `linkat` | ✅ | ✅ | ✅ | |
| `lockf` | ✅ | ✅ | ✅ | |
| `lseek` | ✅ | ✅ | ✅ | |
| `nice` | ✅ | ✅ | ✅ | |
| `pathconf` | ✅ | ✅ | ✅ | |
| `pause` | ✅ | ✅ | ✅ | |
| `pipe` | ✅ | ✅ | ✅ | |
| `pipe2` | ✅ | ✅ | ✅ | |
| `posix_spawn` | ✅ | ✅ | ✅ | |
| `posix_spawnp` | ✅ | ✅ | ✅ | |
| `pread` | ✅ | ✅ | ✅ | |
| `pwrite` | ✅ | ✅ | ✅ | |
| `preadv` | ✅ | ✅ | ✅ | |
| `pwritev` | ✅ | ✅ | ✅ | |
| `preadv2` | ✅ | ✅ | ✅ | |
| `pwritev2` | ✅ | ✅ | ✅ | |
| `read` | ✅ | ✅ | ✅ | |
| `readlink` | ✅ | ✅ | ✅ | |
| `readlinkat` | ✅ | ✅ | ✅ | |
| `readv` | ✅ | ✅ | ✅ | |
| `reboot` | ✅ | ✅ | ✅ | |
| `rename` | ✅ | ✅ | ✅ | |
| `renameat` | ✅ | ✅ | ✅ | |
| `renameat2` | ✅ | ✅ | ✅ | |
| `rewinddir` | ✅ | ✅ | ✅ | |
| `rmdir` | ✅ | ✅ | ✅ | |
| `scandir` | ✅ | ✅ | ✅ | |
| `seekdir` | ✅ | ✅ | ✅ | |
| `select` | ✅ | ✅ | ✅ | |
| `setegid` | ✅ | ✅ | ✅ | |
| `seteuid` | ✅ | ✅ | ✅ | |
| `setgid` | ✅ | ✅ | ✅ | |
| `setgroups` | ✅ | ✅ | ✅ | |
| `sethostname` | ✅ | ✅ | ✅ | |
| `setpgid` | ✅ | ✅ | ✅ | |
| `setpgrp` | ✅ | ✅ | ✅ | |
| `setpriority` | ✅ | ✅ | ✅ | |
| `setregid` | ✅ | ✅ | ✅ | |
| `setresgid` | ✅ | ✅ | ✅ | |
| `setresuid` | ✅ | ✅ | ✅ | |
| `setreuid` | ✅ | ✅ | ✅ | |
| `setrlimit` | ✅ | ✅ | ✅ | |
| `setsid` | ✅ | ✅ | ✅ | |
| `setuid` | ✅ | ✅ | ✅ | |
| `setfsuid` | ✅ | ✅ | ✅ | |
| `setfsgid` | ✅ | ✅ | ✅ | |
| `sleep` | ✅ | ✅ | ✅ | |
| `swab` | ✅ | ✅ | ✅ | |
| `symlink` | ✅ | ✅ | ✅ | |
| `symlinkat` | ✅ | ✅ | ✅ | |
| `sync` | ✅ | ✅ | ✅ | |
| `syncfs` | ✅ | ✅ | ✅ | |
| `sysconf` | ✅ | ✅ | ✅ | |
| `tcgetpgrp` | ✅ | ✅ | ✅ | |
| `tcsetpgrp` | ✅ | ✅ | ✅ | |
| `telldir` | ✅ | ✅ | ✅ | |
| `truncate` | ✅ | ✅ | ✅ | |
| `ttyname` | ✅ | ✅ | ✅ | |
| `ttyname_r` | ✅ | ✅ | ✅ | |
| `unlink` | ✅ | ✅ | ✅ | |
| `unlinkat` | ✅ | ✅ | ✅ | |
| `usleep` | BSD | ✅ | ✅ | ✅ | 已废弃 |
| `vfork` | LEGACY | ✅ | ✅ | ✅ | |
| `vhangup` | ✅ | ✅ | ✅ | |
| `write` | ✅ | ✅ | ✅ | |
| `writev` | ✅ | ✅ | ✅ | |
| `acct` | ✅ | ✅ | ✅ | |
| `chroot` | ✅ | ✅ | ✅ | |
| `crypt` | XSI | ✅ | ⚠️ | ⚠️ | musl 有简化实现 |
| `daemon` | BSD | ✅ | ✅ | ✅ | |
| `encrypt` | XSI | ✅ | ❌ | ❌ | |
| `endusershell` | ✅ | ✅ | ✅ | |
| `euidaccess` | GNU | ✅ | ✅ | ✅ | |
| `fsync` | ✅ | ✅ | ✅ | |
| `ftruncate` | ✅ | ✅ | ✅ | |
| `getdtablesize` | ✅ | ✅ | ✅ | |
| `getentropy` | ✅ | ✅ | ✅ | |
| `getpass` | LEGACY | ✅ | ✅ | ✅ | |
| `getusershell` | ✅ | ✅ | ✅ | |
| `lseek` | ✅ | ✅ | ✅ | |
| `makecontext` | XSI | ✅ | ❌ | ❌ | |
| `swapcontext` | XSI | ✅ | ❌ | ❌ | |
| `_exit` | ✅ | ✅ | ✅ | |
| `F_OK` | ✅ | ✅ | ✅ | |
| `R_OK` | ✅ | ✅ | ✅ | |
| `W_OK` | ✅ | ✅ | ✅ | |
| `X_OK` | ✅ | ✅ | ✅ | |
| `SEEK_SET` | ✅ | ✅ | ✅ | |
| `SEEK_CUR` | ✅ | ✅ | ✅ | |
| `SEEK_END` | ✅ | ✅ | ✅ | |
| `SEEK_DATA` | Linux | ✅ | ✅ | ✅ | |
| `SEEK_HOLE` | Linux | ✅ | ✅ | ✅ | |
| `STDIN_FILENO` | ✅ | ✅ | ✅ | |
| `STDOUT_FILENO` | ✅ | ✅ | ✅ | |
| `STDERR_FILENO` | ✅ | ✅ | ✅ | |
| `_POSIX_VERSION` | ✅ | ✅ | ✅ | |
| `_POSIX2_VERSION` | ✅ | ✅ | ✅ | |
| `_XOPEN_VERSION` | ✅ | ✅ | ✅ | |
| `_SC_*` (全部常量) | ✅ | ✅ | ✅ | ⚠️ 个别值不同 |

