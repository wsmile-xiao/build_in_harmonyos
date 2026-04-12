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


---

## 2.2 POSIX 系统接口

### `<sys/wait.h>`

| 接口/宏 | glibc | musl | OHOS | 说明 |
|---------|:-----:|:----:|:----:|------|
| `wait` | ✅ | ✅ | ✅ | |
| `waitpid` | ✅ | ✅ | ✅ | |
| `waitid` | ✅ | ✅ | ✅ | |
| `wait3` | BSD | ✅ | ✅ | ✅ | |
| `wait4` | BSD | ✅ | ✅ | ✅ | |
| `WIFEXITED` | ✅ | ✅ | ✅ | |
| `WEXITSTATUS` | ✅ | ✅ | ✅ | |
| `WIFSIGNALED` | ✅ | ✅ | ✅ | |
| `WTERMSIG` | ✅ | ✅ | ✅ | |
| `WIFSTOPPED` | ✅ | ✅ | ✅ | |
| `WSTOPSIG` | ✅ | ✅ | ✅ | |
| `WIFCONTINUED` | ✅ | ✅ | ✅ | |
| `WNOHANG` | ✅ | ✅ | ✅ | |
| `WUNTRACED` | ✅ | ✅ | ✅ | |
| `WNOWAIT` | ✅ | ✅ | ✅ | |
| `WEXITED` | ✅ | ✅ | ✅ | |
| `WSTOPPED` | ✅ | ✅ | ✅ | |
| `WCONTINUED` | ✅ | ✅ | ✅ | |

### `<sys/resource.h>`

| 接口/宏 | glibc | musl | OHOS | 说明 |
|---------|:-----:|:----:|:----:|------|
| `getrlimit` | ✅ | ✅ | ✅ | |
| `setrlimit` | ✅ | ✅ | ✅ | |
| `getrlimit64` | ✅ | ✅ | ✅ | |
| `setrlimit64` | ✅ | ✅ | ✅ | |
| `prlimit` | ✅ | ✅ | ✅ | |
| `prlimit64` | ✅ | ✅ | ✅ | |
| `getrusage` | ✅ | ✅ | ✅ | |
| `getpriority` | ✅ | ✅ | ✅ | |
| `setpriority` | ✅ | ✅ | ✅ | |
| `struct rlimit` | ✅ | ✅ | ✅ | musl 始终 64-bit |
| `struct rusage` | ✅ | ✅ | ✅ | |
| `RLIMIT_AS` | ✅ | ✅ | ✅ | |
| `RLIMIT_CORE` | ✅ | ✅ | ✅ | |
| `RLIMIT_CPU` | ✅ | ✅ | ✅ | |
| `RLIMIT_DATA` | ✅ | ✅ | ✅ | |
| `RLIMIT_FSIZE` | ✅ | ✅ | ✅ | |
| `RLIMIT_LOCKS` | ✅ | ✅ | ✅ | |
| `RLIMIT_MEMLOCK` | ✅ | ✅ | ✅ | |
| `RLIMIT_MSGQUEUE` | ✅ | ✅ | ✅ | |
| `RLIMIT_NICE` | ✅ | ✅ | ✅ | |
| `RLIMIT_NOFILE` | ✅ | ✅ | ✅ | |
| `RLIMIT_NPROC` | ✅ | ✅ | ✅ | |
| `RLIMIT_NPTS` | ✅ | ✅ | ✅ | |
| `RLIMIT_RSS` | ✅ | ✅ | ✅ | |
| `RLIMIT_RTPRIO` | ✅ | ✅ | ✅ | |
| `RLIMIT_RTTIME` | ✅ | ✅ | ✅ | |
| `RLIMIT_SIGPENDING` | ✅ | ✅ | ✅ | |
| `RLIMIT_STACK` | ✅ | ✅ | ✅ | |
| `RLIM_INFINITY` | ✅ | ✅ | ✅ | |
| `PRIO_MIN` | ✅ | ✅ | ✅ | |
| `PRIO_MAX` | ✅ | ✅ | ✅ | |
| `PRIO_PROCESS` | ✅ | ✅ | ✅ | |
| `PRIO_PGRP` | ✅ | ✅ | ✅ | |
| `PRIO_USER` | ✅ | ✅ | ✅ | |
| `RUSAGE_SELF` | ✅ | ✅ | ✅ | |
| `RUSAGE_CHILDREN` | ✅ | ✅ | ✅ | |
| `RUSAGE_THREAD` | Linux | ✅ | ✅ | ✅ | |
| `ioprio_get` | Linux | ✅ | ✅ | ✅ | |
| `ioprio_set` | Linux | ✅ | ✅ | ✅ | |

### `<signal.h>` (POSIX 信号扩展)

| 接口/宏 | glibc | musl | OHOS | 说明 |
|---------|:-----:|:----:|:----:|------|
| `kill` | ✅ | ✅ | ✅ | |
| `raise` | ✅ | ✅ | ✅ | |
| `sigaction` | ✅ | ✅ | ✅ | |
| `sigaddset` | ✅ | ✅ | ✅ | |
| `sigaltstack` | ✅ | ✅ | ✅ | |
| `sigdelset` | ✅ | ✅ | ✅ | |
| `sigemptyset` | ✅ | ✅ | ✅ | |
| `sigfillset` | ✅ | ✅ | ✅ | |
| `sigismember` | ✅ | ✅ | ✅ | |
| `sigpending` | ✅ | ✅ | ✅ | |
| `sigprocmask` | ✅ | ✅ | ✅ | |
| `sigsuspend` | ✅ | ✅ | ✅ | |
| `sigtimedwait` | ✅ | ✅ | ✅ | |
| `sigwait` | ✅ | ✅ | ✅ | |
| `sigwaitinfo` | ✅ | ✅ | ✅ | |
| `sigqueue` | ✅ | ✅ | ✅ | |
| `killpg` | ✅ | ✅ | ✅ | |
| `pthread_kill` | ✅ | ✅ | ✅ | |
| `pthread_sigmask` | ✅ | ✅ | ✅ | |
| `sig_atomic_t` | ✅ | ✅ | ✅ | |
| `sigset_t` | ✅ | ✅ | ✅ | |
| `siginfo_t` | ✅ | ✅ | ✅ | |
| `pid_t` | ✅ | ✅ | ✅ | |
| `uid_t` | ✅ | ✅ | ✅ | |
| `SA_NOCLDSTOP` | ✅ | ✅ | ✅ | |
| `SA_NOCLDWAIT` | ✅ | ✅ | ✅ | |
| `SA_NODEFER` | ✅ | ✅ | ✅ | |
| `SA_ONSTACK` | ✅ | ✅ | ✅ | |
| `SA_RESETHAND` | ✅ | ✅ | ✅ | |
| `SA_RESTART` | ✅ | ✅ | ✅ | |
| `SA_SIGINFO` | ✅ | ✅ | ✅ | |
| `SA_INTERRUPT` | ✅ | ❌ | ❌ | musl 不提供 |
| `SA_RESTORER` | ✅ | ❌ | ❌ | musl 内部处理 |
| `SIG_BLOCK` | ✅ | ✅ | ✅ | |
| `SIG_SETMASK` | ✅ | ✅ | ✅ | |
| `SIG_UNBLOCK` | ✅ | ✅ | ✅ | |
| `SI_USER` | ✅ | ✅ | ✅ | |
| `SI_KERNEL` | ✅ | ✅ | ✅ | |
| `SI_QUEUE` | ✅ | ✅ | ✅ | |
| `SI_TIMER` | ✅ | ✅ | ✅ | |
| `SI_MESGQ` | ✅ | ✅ | ✅ | |
| `SI_ASYNCIO` | ✅ | ✅ | ✅ | |
| `SI_SIGIO` | ✅ | ✅ | ✅ | |
| `SI_TKILL` | ✅ | ✅ | ✅ | |
| `ILL_*` 常量 | ✅ | ✅ | ✅ | |
| `FPE_*` 常量 | ✅ | ✅ | ✅ | |
| `SEGV_*` 常量 | ✅ | ✅ | ✅ | |
| `BUS_*` 常量 | ✅ | ✅ | ✅ | |
| `TRAP_*` 常量 | ✅ | ✅ | ✅ | |
| `CLD_*` 常量 | ✅ | ✅ | ✅ | |
| `POLL_*` 常量 | ✅ | ✅ | ✅ | |
| `SIGRTMIN` | ✅ | ✅ | ✅ | |
| `SIGRTMAX` | ✅ | ✅ | ✅ | |
| `NSIG` | ✅ | ✅ | ✅ | |
| `_NSIG` | ✅ | ✅ | ✅ | |
| `signalfd` | Linux | ✅ | ✅ | ✅ | |
| `sigprocmask` | ✅ | ✅ | ✅ | |

### `<grp.h>` & `<pwd.h>`

| 接口 | glibc | musl | OHOS | 说明 |
|------|:-----:|:----:|:----:|------|
| `getgrgid` | ✅ | ✅ | ✅ | |
| `getgrnam` | ✅ | ✅ | ✅ | |
| `getgrgid_r` | ✅ | ✅ | ✅ | |
| `getgrnam_r` | ✅ | ✅ | ✅ | |
| `setgrent` | ✅ | ✅ | ✅ | |
| `getgrent` | ✅ | ✅ | ✅ | |
| `endgrent` | ✅ | ✅ | ✅ | |
| `getgrgid` | ✅ | ✅ | ✅ | |
| `struct group` | ✅ | ✅ | ✅ | |
| `getpwnam` | ✅ | ✅ | ✅ | |
| `getpwuid` | ✅ | ✅ | ✅ | |
| `getpwnam_r` | ✅ | ✅ | ✅ | |
| `getpwuid_r` | ✅ | ✅ | ✅ | |
| `setpwent` | ✅ | ✅ | ✅ | |
| `getpwent` | ✅ | ✅ | ✅ | |
| `endpwent` | ✅ | ✅ | ✅ | |
| `struct passwd` | ✅ | ✅ | ✅ | |
| `getpwuid` | ✅ | ✅ | ✅ | |

---

## 2.3 POSIX 网络接口

### `<sys/socket.h>`

| 接口/宏 | glibc | musl | OHOS | 说明 |
|---------|:-----:|:----:|:----:|------|
| `socket` | ✅ | ✅ | ✅ | |
| `bind` | ✅ | ✅ | ✅ | |
| `listen` | ✅ | ✅ | ✅ | |
| `accept` | ✅ | ✅ | ✅ | |
| `accept4` | Linux | ✅ | ✅ | ✅ | |
| `connect` | ✅ | ✅ | ✅ | |
| `send` | ✅ | ✅ | ✅ | |
| `sendto` | ✅ | ✅ | ✅ | |
| `sendmsg` | ✅ | ✅ | ✅ | |
| `sendmmsg` | Linux | ✅ | ✅ | ✅ | |
| `recv` | ✅ | ✅ | ✅ | |
| `recvfrom` | ✅ | ✅ | ✅ | |
| `recvmsg` | ✅ | ✅ | ✅ | |
| `recvmmsg` | Linux | ✅ | ✅ | ✅ | |
| `shutdown` | ✅ | ✅ | ✅ | |
| `getsockname` | ✅ | ✅ | ✅ | |
| `getpeername` | ✅ | ✅ | ✅ | |
| `socketpair` | ✅ | ✅ | ✅ | |
| `getsockopt` | ✅ | ✅ | ✅ | |
| `setsockopt` | ✅ | ✅ | ✅ | |
| `socklen_t` | ✅ | ✅ | ✅ | |
| `sa_family_t` | ✅ | ✅ | ✅ | |
| `AF_UNIX` | ✅ | ✅ | ✅ | |
| `AF_INET` | ✅ | ✅ | ✅ | |
| `AF_INET6` | ✅ | ✅ | ✅ | |
| `AF_UNSPEC` | ✅ | ✅ | ✅ | |
| `AF_PACKET` | Linux | ✅ | ✅ | ✅ | |
| `AF_NETLINK` | Linux | ✅ | ✅ | ✅ | |
| `AF_VSOCK` | Linux | ✅ | ✅ | ✅ | |
| `AF_XDP` | Linux | ✅ | ✅ | ✅ | |
| `SOCK_STREAM` | ✅ | ✅ | ✅ | |
| `SOCK_DGRAM` | ✅ | ✅ | ✅ | |
| `SOCK_RAW` | Linux | ✅ | ✅ | ✅ | |
| `SOCK_SEQPACKET` | ✅ | ✅ | ✅ | |
| `SOCK_NONBLOCK` | Linux | ✅ | ✅ | ✅ | |
| `SOCK_CLOEXEC` | Linux | ✅ | ✅ | ✅ | |
| `SOL_SOCKET` | ✅ | ✅ | ✅ | |
| `SOL_IP` | Linux | ✅ | ✅ | ✅ | |
| `SOL_IPV6` | Linux | ✅ | ✅ | ✅ | |
| `SOL_ICMPV6` | Linux | ✅ | ✅ | ✅ | |
| `SOL_TCP` | Linux | ✅ | ✅ | ✅ | |
| `SOL_UDP` | Linux | ✅ | ✅ | ✅ | |
| `SO_DEBUG` | ✅ | ✅ | ✅ | |
| `SO_ACCEPTCONN` | ✅ | ✅ | ✅ | |
| `SO_BROADCAST` | ✅ | ✅ | ✅ | |
| `SO_REUSEADDR` | ✅ | ✅ | ✅ | |
| `SO_REUSEPORT` | ✅ | ✅ | ✅ | |
| `SO_KEEPALIVE` | ✅ | ✅ | ✅ | |
| `SO_LINGER` | ✅ | ✅ | ✅ | |
| `SO_OOBINLINE` | ✅ | ✅ | ✅ | |
| `SO_SNDBUF` | ✅ | ✅ | ✅ | |
| `SO_RCVBUF` | ✅ | ✅ | ✅ | |
| `SO_SNDLOWAT` | ✅ | ✅ | ✅ | |
| `SO_RCVLOWAT` | ✅ | ✅ | ✅ | |
| `SO_SNDTIMEO` | ✅ | ✅ | ✅ | |
| `SO_RCVTIMEO` | ✅ | ✅ | ✅ | |
| `SO_ERROR` | ✅ | ✅ | ✅ | |
| `SO_TYPE` | ✅ | ✅ | ✅ | |
| `SO_DONTROUTE` | ✅ | ✅ | ✅ | |
| `SO_TIMESTAMP` | Linux | ✅ | ✅ | ✅ | |
| `SO_TIMESTAMPNS` | Linux | ✅ | ✅ | ✅ | |
| `SO_TIMESTAMPING` | Linux | ✅ | ✅ | ✅ | |
| `SO_MARK` | Linux | ✅ | ✅ | ✅ | |
| `SO_PASSCRED` | Linux | ✅ | ✅ | ✅ | |
| `SO_PEERCRED` | Linux | ✅ | ✅ | ✅ | |
| `SO_PEEK_OFF` | Linux | ✅ | ✅ | ✅ | |
| `SO_PRIORITY` | Linux | ✅ | ✅ | ✅ | |
| `SO_BINDTODEVICE` | Linux | ✅ | ✅ | ✅ | |
| `SO_ATTACH_FILTER` | Linux | ✅ | ✅ | ✅ | |
| `SO_DETACH_FILTER` | Linux | ✅ | ✅ | ✅ | |
| `SO_ATTACH_BPF` | Linux | ✅ | ✅ | ✅ | |
| `SO_ATTACH_REUSEPORT_CBPF` | Linux | ✅ | ✅ | ✅ | |
| `SO_ATTACH_REUSEPORT_EBPF` | Linux | ✅ | ✅ | ✅ | |
| `SO_ZEROCOPY` | Linux | ✅ | ✅ | ✅ | |
| `SO_BUSY_POLL` | Linux | ✅ | ✅ | ✅ | |
| `SO_TXTIME` | Linux | ✅ | ✅ | ✅ | |
| `MSG_OOB` | ✅ | ✅ | ✅ | |
| `MSG_PEEK` | ✅ | ✅ | ✅ | |
| `MSG_DONTROUTE` | ✅ | ✅ | ✅ | |
| `MSG_WAITALL` | ✅ | ✅ | ✅ | |
| `MSG_DONTWAIT` | Linux | ✅ | ✅ | ✅ | |
| `MSG_NOSIGNAL` | Linux | ✅ | ✅ | ✅ | |
| `MSG_CTRUNC` | ✅ | ✅ | ✅ | |
| `MSG_TRUNC` | ✅ | ✅ | ✅ | |
| `MSG_EOR` | ✅ | ✅ | ✅ | |
| `MSG_MORE` | Linux | ✅ | ✅ | ✅ | |
| `MSG_WAITFORONE` | Linux | ✅ | ✅ | ✅ | |
| `MSG_ZEROCOPY` | Linux | ✅ | ✅ | ✅ | |
| `SCM_RIGHTS` | ✅ | ✅ | ✅ | |
| `SCM_CREDENTIALS` | Linux | ✅ | ✅ | ✅ | |
| `struct sockaddr` | ✅ | ✅ | ✅ | |
| `struct sockaddr_storage` | ✅ | ✅ | ✅ | |

### `<netinet/in.h>` & `<arpa/inet.h>`

| 接口/宏 | glibc | musl | OHOS | 说明 |
|---------|:-----:|:----:|:----:|------|
| `htonl` | ✅ | ✅ | ✅ | |
| `htons` | ✅ | ✅ | ✅ | |
| `ntohl` | ✅ | ✅ | ✅ | |
| `ntohs` | ✅ | ✅ | ✅ | |
| `inet_addr` | ✅ | ✅ | ✅ | |
| `inet_ntoa` | ✅ | ✅ | ✅ | |
| `inet_pton` | ✅ | ✅ | ✅ | |
| `inet_ntop` | ✅ | ✅ | ✅ | |
| `inet_aton` | BSD | ✅ | ✅ | ✅ | |
| `inet_ntop_r` | GNU | ✅ | ❌ | ❌ | inet_ntop 已线程安全 |
| `inet_makeaddr` | ✅ | ✅ | ✅ | |
| `inet_netof` | ✅ | ✅ | ✅ | |
| `inet_network` | ✅ | ✅ | ✅ | |
| `INADDR_ANY` | ✅ | ✅ | ✅ | |
| `INADDR_BROADCAST` | ✅ | ✅ | ✅ | |
| `INADDR_LOOPBACK` | ✅ | ✅ | ✅ | |
| `INADDR_NONE` | ✅ | ✅ | ✅ | |
| `IN6ADDR_ANY_INIT` | ✅ | ✅ | ✅ | |
| `IN6ADDR_LOOPBACK_INIT` | ✅ | ✅ | ✅ | |
| `in_addr_t` | ✅ | ✅ | ✅ | |
| `in_port_t` | ✅ | ✅ | ✅ | |
| `struct in_addr` | ✅ | ✅ | ✅ | |
| `struct in6_addr` | ✅ | ✅ | ✅ | |
| `struct sockaddr_in` | ✅ | ✅ | ✅ | |
| `struct sockaddr_in6` | ✅ | ✅ | ✅ | |
| `IPPROTO_IP` | ✅ | ✅ | ✅ | |
| `IPPROTO_ICMP` | ✅ | ✅ | ✅ | |
| `IPPROTO_TCP` | ✅ | ✅ | ✅ | |
| `IPPROTO_UDP` | ✅ | ✅ | ✅ | |
| `IPPROTO_RAW` | ✅ | ✅ | ✅ | |
| `IPPROTO_IPV6` | ✅ | ✅ | ✅ | |
| `IPV6_V6ONLY` | ✅ | ✅ | ✅ | |
| `IPV6_UNICAST_HOPS` | ✅ | ✅ | ✅ | |
| `IPV6_MULTICAST_IF` | ✅ | ✅ | ✅ | |
| `IPV6_MULTICAST_HOPS` | ✅ | ✅ | ✅ | |
| `IPV6_MULTICAST_LOOP` | ✅ | ✅ | ✅ | |
| `IPV6_JOIN_GROUP` | ✅ | ✅ | ✅ | |
| `IPV6_LEAVE_GROUP` | ✅ | ✅ | ✅ | |
| `IPV6_RECVPKTINFO` | ✅ | ✅ | ✅ | |
| `IPV6_PKTINFO` | ✅ | ✅ | ✅ | |
| `IPV6_RECVHOPLIMIT` | ✅ | ✅ | ✅ | |
| `IPV6_HOPLIMIT` | ✅ | ✅ | ✅ | |
| `IPV6_RECVRTHDR` | ✅ | ✅ | ✅ | |
| `IPV6_RTHDR` | ✅ | ✅ | ✅ | |
| `IPV6_RECVTCLASS` | ✅ | ✅ | ✅ | |
| `IPV6_TCLASS` | ✅ | ✅ | ✅ | |
| `IPV6_RECVHOPOPTS` | ✅ | ✅ | ✅ | |
| `IPV6_HOPOPTS` | ✅ | ✅ | ✅ | |
| `IPV6_RECVDSTOPTS` | ✅ | ✅ | ✅ | |
| `IPV6_DSTOPTS` | ✅ | ✅ | ✅ | |
| `struct ipv6_mreq` | ✅ | ✅ | ✅ | |
| `struct in6_pktinfo` | ✅ | ✅ | ✅ | |
| `IP_TOS` | ✅ | ✅ | ✅ | |
| `IP_TTL` | ✅ | ✅ | ✅ | |
| `IP_HDRINCL` | ✅ | ✅ | ✅ | |
| `IP_OPTIONS` | ✅ | ✅ | ✅ | |
| `IP_PKTINFO` | ✅ | ✅ | ✅ | |
| `IP_RECVTOS` | ✅ | ✅ | ✅ | |
| `IP_MTU_DISCOVER` | ✅ | ✅ | ✅ | |
| `IP_MULTICAST_IF` | ✅ | ✅ | ✅ | |
| `IP_MULTICAST_TTL` | ✅ | ✅ | ✅ | |
| `IP_MULTICAST_LOOP` | ✅ | ✅ | ✅ | |
| `IP_ADD_MEMBERSHIP` | ✅ | ✅ | ✅ | |
| `IP_DROP_MEMBERSHIP` | ✅ | ✅ | ✅ | |

### `<netdb.h>`

| 接口/宏 | glibc | musl | OHOS | 说明 |
|---------|:-----:|:----:|:----:|------|
| `getaddrinfo` | ✅ | ✅ | ✅ | ⚠️ AI_ADDRCONFIG 处理差异 |
| `getnameinfo` | ✅ | ✅ | ✅ | |
| `freeaddrinfo` | ✅ | ✅ | ✅ | |
| `gai_strerror` | ✅ | ✅ | ✅ | |
| `gethostbyname` | ✅ | ✅ | ✅ | |
| `gethostbyaddr` | ✅ | ✅ | ✅ | |
| `gethostent` | ✅ | ✅ | ✅ | |
| `sethostent` | ✅ | ✅ | ✅ | |
| `endhostent` | ✅ | ✅ | ✅ | |
| `gethostbyname2` | ✅ | ✅ | ✅ | |
| `getprotobyname` | ✅ | ✅ | ✅ | |
| `getprotobynumber` | ✅ | ✅ | ✅ | |
| `getservbyname` | ✅ | ✅ | ✅ | |
| `getservbyport` | ✅ | ✅ | ✅ | |
| `getservent` | ✅ | ✅ | ✅ | |
| `struct addrinfo` | ✅ | ✅ | ✅ | |
| `struct hostent` | ✅ | ✅ | ✅ | |
| `struct protoent` | ✅ | ✅ | ✅ | |
| `struct servent` | ✅ | ✅ | ✅ | |
| `AI_PASSIVE` | ✅ | ✅ | ✅ | |
| `AI_CANONNAME` | ✅ | ✅ | ✅ | |
| `AI_NUMERICHOST` | ✅ | ✅ | ✅ | |
| `AI_NUMERICSERV` | ✅ | ✅ | ✅ | |
| `AI_V4MAPPED` | ✅ | ✅ | ✅ | |
| `AI_ALL` | ✅ | ✅ | ✅ | |
| `AI_ADDRCONFIG` | ✅ | ✅ | ✅ | |
| `AI_IDN` | GNU | ✅ | ❌ | ❌ | |
| `AI_CANONIDN` | GNU | ✅ | ❌ | ❌ | |
| `AI_IDN_ALLOW_UNASSIGNED` | GNU | ✅ | ❌ | ❌ | |
| `AI_IDN_USE_STD3_ASCII_RULES` | GNU | ✅ | ❌ | ❌ | |
| `NI_NUMERICHOST` | ✅ | ✅ | ✅ | |
| `NI_NUMERICSERV` | ✅ | ✅ | ✅ | |
| `NI_NOFQDN` | ✅ | ✅ | ✅ | |
| `NI_NAMEREQD` | ✅ | ✅ | ✅ | |
| `NI_DGRAM` | ✅ | ✅ | ✅ | |
| `NI_IDN` | GNU | ✅ | ❌ | ❌ | |
| `EAI_*` 常量 | ✅ | ✅ | ✅ | |
| `h_errno` | ✅ | ✅ | ✅ | |
| `hstrerror` | ✅ | ✅ | ✅ | |

### `<ifaddrs.h>`

| 接口 | glibc | musl | OHOS | 说明 |
|------|:-----:|:----:|:----:|------|
| `getifaddrs` | ✅ | ✅ | ✅ | |
| `freeifaddrs` | ✅ | ✅ | ✅ | |
| `struct ifaddrs` | ✅ | ✅ | ✅ | |


---

## 2.4 POSIX 线程 (pthread)

### `<pthread.h>`

| 接口/宏 | glibc | musl | OHOS | 说明 |
|---------|:-----:|:----:|:----:|------|
| `pthread_create` | ✅ | ✅ | ✅ | ⚠️ 默认栈大小差异: musl 128KB, glibc 2-8MB |
| `pthread_join` | ✅ | ✅ | ✅ | |
| `pthread_detach` | ✅ | ✅ | ✅ | |
| `pthread_exit` | ✅ | ✅ | ✅ | |
| `pthread_self` | ✅ | ✅ | ✅ | |
| `pthread_equal` | ✅ | ✅ | ✅ | |
| `pthread_once` | ✅ | ✅ | ✅ | |
| `pthread_atfork` | ✅ | ✅ | ✅ | |
| `pthread_cancel` | ✅ | ✅ | ✅ | |
| `pthread_testcancel` | ✅ | ✅ | ✅ | |
| `pthread_setcancelstate` | ✅ | ✅ | ✅ | |
| `pthread_setcanceltype` | ✅ | ✅ | ✅ | |
| `pthread_kill` | ✅ | ✅ | ✅ | |
| `pthread_sigmask` | ✅ | ✅ | ✅ | |
| `pthread_setaffinity_np` | ✅ | ✅ | ✅ | |
| `pthread_getaffinity_np` | ✅ | ✅ | ✅ | |
| `pthread_getname_np` | ✅ | ✅ | ✅ | |
| `pthread_setname_np` | ✅ | ✅ | ✅ | ⚠️ 签名可能有差异 |
| `pthread_getattr_np` | ✅ | ✅ | ✅ | |
| `pthread_getattr_default_np` | ✅ | ❌ | ❌ | |
| `pthread_setattr_default_np` | ✅ | ❌ | ❌ | |
| `pthread_yield` | ✅ | ✅ | ✅ | |
| `pthread_cleanup_push` | ✅ | ✅ | ✅ | |
| `pthread_cleanup_pop` | ✅ | ✅ | ✅ | |
| `pthread_mutex_init` | ✅ | ✅ | ✅ | |
| `pthread_mutex_destroy` | ✅ | ✅ | ✅ | |
| `pthread_mutex_lock` | ✅ | ✅ | ✅ | |
| `pthread_mutex_unlock` | ✅ | ✅ | ✅ | |
| `pthread_mutex_trylock` | ✅ | ✅ | ✅ | |
| `pthread_mutex_timedlock` | ✅ | ✅ | ✅ | |
| `pthread_mutex_consistent` | ✅ | ✅ | ✅ | |
| `pthread_mutexattr_init` | ✅ | ✅ | ✅ | |
| `pthread_mutexattr_destroy` | ✅ | ✅ | ✅ | |
| `pthread_mutexattr_settype` | ✅ | ✅ | ✅ | |
| `pthread_mutexattr_gettype` | ✅ | ✅ | ✅ | |
| `pthread_mutexattr_setpshared` | ✅ | ✅ | ✅ | |
| `pthread_mutexattr_getpshared` | ✅ | ✅ | ✅ | |
| `pthread_mutexattr_setprotocol` | ✅ | ✅ | ✅ | |
| `pthread_mutexattr_getprotocol` | ✅ | ✅ | ✅ | |
| `pthread_mutexattr_setprioceiling` | ✅ | ✅ | ✅ | |
| `pthread_mutexattr_getprioceiling` | ✅ | ✅ | ✅ | |
| `pthread_mutexattr_setrobust` | ✅ | ✅ | ✅ | |
| `pthread_mutexattr_getrobust` | ✅ | ✅ | ✅ | |
| `pthread_cond_init` | ✅ | ✅ | ✅ | |
| `pthread_cond_destroy` | ✅ | ✅ | ✅ | |
| `pthread_cond_wait` | ✅ | ✅ | ✅ | |
| `pthread_cond_timedwait` | ✅ | ✅ | ✅ | |
| `pthread_cond_signal` | ✅ | ✅ | ✅ | |
| `pthread_cond_broadcast` | ✅ | ✅ | ✅ | |
| `pthread_condattr_init` | ✅ | ✅ | ✅ | |
| `pthread_condattr_destroy` | ✅ | ✅ | ✅ | |
| `pthread_condattr_setpshared` | ✅ | ✅ | ✅ | |
| `pthread_condattr_setclock` | ✅ | ✅ | ✅ | |
| `pthread_rwlock_init` | ✅ | ✅ | ✅ | |
| `pthread_rwlock_destroy` | ✅ | ✅ | ✅ | |
| `pthread_rwlock_rdlock` | ✅ | ✅ | ✅ | |
| `pthread_rwlock_tryrdlock` | ✅ | ✅ | ✅ | |
| `pthread_rwlock_timedrdlock` | ✅ | ✅ | ✅ | |
| `pthread_rwlock_wrlock` | ✅ | ✅ | ✅ | |
| `pthread_rwlock_trywrlock` | ✅ | ✅ | ✅ | |
| `pthread_rwlock_timedwrlock` | ✅ | ✅ | ✅ | |
| `pthread_rwlockattr_init` | ✅ | ✅ | ✅ | |
| `pthread_rwlockattr_destroy` | ✅ | ✅ | ✅ | |
| `pthread_rwlockattr_setpshared` | ✅ | ✅ | ✅ | |
| `pthread_rwlockattr_setkind_np` | ✅ | ✅ | ✅ | |
| `pthread_key_create` | ✅ | ✅ | ✅ | |
| `pthread_key_delete` | ✅ | ✅ | ✅ | |
| `pthread_getspecific` | ✅ | ✅ | ✅ | |
| `pthread_setspecific` | ✅ | ✅ | ✅ | |
| `pthread_attr_init` | ✅ | ✅ | ✅ | |
| `pthread_attr_destroy` | ✅ | ✅ | ✅ | |
| `pthread_attr_setstacksize` | ✅ | ✅ | ✅ | |
| `pthread_attr_getstacksize` | ✅ | ✅ | ✅ | |
| `pthread_attr_setstackaddr` | ✅ | ✅ | ✅ | |
| `pthread_attr_getstackaddr` | ✅ | ✅ | ✅ | |
| `pthread_attr_setguardsize` | ✅ | ✅ | ✅ | |
| `pthread_attr_getguardsize` | ✅ | ✅ | ✅ | |
| `pthread_attr_setdetachstate` | ✅ | ✅ | ✅ | |
| `pthread_attr_getdetachstate` | ✅ | ✅ | ✅ | |
| `pthread_attr_setscope` | ✅ | ✅ | ✅ | |
| `pthread_attr_getscope` | ✅ | ✅ | ✅ | |
| `pthread_attr_setinheritsched` | ✅ | ✅ | ✅ | |
| `pthread_attr_getinheritsched` | ✅ | ✅ | ✅ | |
| `pthread_attr_setschedpolicy` | ✅ | ✅ | ✅ | |
| `pthread_attr_getschedpolicy` | ✅ | ✅ | ✅ | |
| `pthread_attr_setschedparam` | ✅ | ✅ | ✅ | |
| `pthread_attr_getschedparam` | ✅ | ✅ | ✅ | |
| `pthread_attr_setschedpriority` | ✅ | ✅ | ✅ | |
| `pthread_attr_getschedpriority` | ✅ | ✅ | ✅ | |
| `pthread_spin_init` | ✅ | ✅ | ✅ | |
| `pthread_spin_destroy` | ✅ | ✅ | ✅ | |
| `pthread_spin_lock` | ✅ | ✅ | ✅ | |
| `pthread_spin_trylock` | ✅ | ✅ | ✅ | |
| `pthread_spin_unlock` | ✅ | ✅ | ✅ | |
| `pthread_barrier_init` | ✅ | ✅ | ✅ | |
| `pthread_barrier_destroy` | ✅ | ✅ | ✅ | |
| `pthread_barrier_wait` | ✅ | ✅ | ✅ | |
| `pthread_barrierattr_init` | ✅ | ✅ | ✅ | |
| `pthread_barrierattr_destroy` | ✅ | ✅ | ✅ | |
| `pthread_barrierattr_setpshared` | ✅ | ✅ | ✅ | |
| `pthread_barrierattr_getpshared` | ✅ | ✅ | ✅ | |
| `pthread_rwlock_clockrdlock` | ✅ | ✅ | ✅ | |
| `pthread_rwlock_clockwrlock` | ✅ | ✅ | ✅ | |
| `pthread_mutex_clocklock` | ✅ | ✅ | ✅ | |
| `pthread_cond_clockwait` | ✅ | ✅ | ✅ | |
| `pthread_getcpuclockid` | ✅ | ✅ | ✅ | |
| `pthread_clockjoin_np` | ✅ | ✅ | ✅ | |
| `pthread_tryjoin_np` | ✅ | ❌ | ❌ | |
| `pthread_timedjoin_np` | ✅ | ❌ | ❌ | |
| `pthread_setconcurrency` | XSI | ✅ | ❌ | ❌ | |
| `pthread_getconcurrency` | XSI | ✅ | ❌ | ❌ | |
| `pthread_mutex_getprioceiling` | XSI | ✅ | ✅ | ✅ | |
| `PTHREAD_CREATE_JOINABLE` | ✅ | ✅ | ✅ | |
| `PTHREAD_CREATE_DETACHED` | ✅ | ✅ | ✅ | |
| `PTHREAD_MUTEX_NORMAL` | ✅ | ✅ | ✅ | |
| `PTHREAD_MUTEX_ERRORCHECK` | ✅ | ✅ | ✅ | |
| `PTHREAD_MUTEX_RECURSIVE` | ✅ | ✅ | ✅ | |
| `PTHREAD_MUTEX_DEFAULT` | ✅ | ✅ | ✅ | |
| `PTHREAD_PRIO_NONE` | ✅ | ✅ | ✅ | |
| `PTHREAD_PRIO_INHERIT` | ✅ | ✅ | ✅ | |
| `PTHREAD_PRIO_PROTECT` | ✅ | ✅ | ✅ | |
| `PTHREAD_SCOPE_SYSTEM` | ✅ | ✅ | ✅ | |
| `PTHREAD_SCOPE_PROCESS` | ✅ | ✅ | ✅ | |
| `PTHREAD_INHERIT_SCHED` | ✅ | ✅ | ✅ | |
| `PTHREAD_EXPLICIT_SCHED` | ✅ | ✅ | ✅ | |
| `PTHREAD_STACK_MIN` | ✅ | ✅ | ✅ | |
| `PTHREAD_MUTEX_ROBUST` | ✅ | ✅ | ✅ | |
| `pthread_t` | ✅ | ✅ | ✅ | |
| `pthread_mutex_t` | ✅ | ✅ | ✅ | |
| `pthread_cond_t` | ✅ | ✅ | ✅ | |
| `pthread_rwlock_t` | ✅ | ✅ | ✅ | |
| `pthread_key_t` | ✅ | ✅ | ✅ | |
| `pthread_once_t` | ✅ | ✅ | ✅ | |
| `pthread_attr_t` | ✅ | ✅ | ✅ | |
| `pthread_mutexattr_t` | ✅ | ✅ | ✅ | |

---

## 2.5 内存映射

### `<sys/mman.h>`

| 接口/宏 | glibc | musl | OHOS | 说明 |
|---------|:-----:|:----:|:----:|------|
| `mmap` | ✅ | ✅ | ✅ | |
| `munmap` | ✅ | ✅ | ✅ | |
| `mprotect` | ✅ | ✅ | ✅ | |
| `msync` | ✅ | ✅ | ✅ | |
| `mlock` | ✅ | ✅ | ✅ | |
| `munlock` | ✅ | ✅ | ✅ | |
| `mlockall` | ✅ | ✅ | ✅ | |
| `munlockall` | ✅ | ✅ | ✅ | |
| `mlock2` | Linux | ✅ | ✅ | ✅ | |
| `mremap` | ✅ | ✅ | ✅ | |
| `madvise` | ✅ | ✅ | ✅ | |
| `posix_madvise` | ✅ | ✅ | ✅ | |
| `mempcpy` | ✅ | ✅ | ✅ | |
| `shm_open` | ✅ | ✅ | ✅ | |
| `shm_unlink` | ✅ | ✅ | ✅ | |
| `memfd_create` | Linux | ✅ | ✅ | ✅ | |
| `MAP_SHARED` | ✅ | ✅ | ✅ | |
| `MAP_PRIVATE` | ✅ | ✅ | ✅ | |
| `MAP_ANONYMOUS` | ✅ | ✅ | ✅ | |
| `MAP_ANON` | BSD | ✅ | ✅ | ✅ | |
| `MAP_FIXED` | ✅ | ✅ | ✅ | |
| `MAP_FIXED_NOREPLACE` | Linux | ✅ | ✅ | ✅ | |
| `MAP_GROWSDOWN` | ✅ | ✅ | ✅ | |
| `MAP_DENYWRITE` | ✅ | ✅ | ✅ | |
| `MAP_EXECUTABLE` | ✅ | ✅ | ✅ | |
| `MAP_LOCKED` | ✅ | ✅ | ✅ | |
| `MAP_NORESERVE` | ✅ | ✅ | ✅ | |
| `MAP_POPULATE` | ✅ | ✅ | ✅ | |
| `MAP_NONBLOCK` | ✅ | ✅ | ✅ | |
| `MAP_STACK` | ✅ | ✅ | ✅ | |
| `MAP_HUGETLB` | ✅ | ✅ | ✅ | |
| `MAP_HUGE_SHIFT` | ✅ | ✅ | ✅ | |
| `MAP_HUGE_MASK` | ✅ | ✅ | ✅ | |
| `MAP_SYNC` | ✅ | ✅ | ✅ | |
| `MAP_SHARED_VALIDATE` | ✅ | ✅ | ✅ | |
| `MAP_FILE` | ✅ | ✅ | ✅ | |
| `MAP_32BIT` | ✅ | ✅ | ✅ | |
| `PROT_READ` | ✅ | ✅ | ✅ | |
| `PROT_WRITE` | ✅ | ✅ | ✅ | |
| `PROT_EXEC` | ✅ | ✅ | ✅ | |
| `PROT_NONE` | ✅ | ✅ | ✅ | |
| `PROT_GROWSDOWN` | ✅ | ✅ | ✅ | |
| `PROT_GROWSUP` | ✅ | ✅ | ✅ | |
| `MCL_CURRENT` | ✅ | ✅ | ✅ | |
| `MCL_FUTURE` | ✅ | ✅ | ✅ | |
| `MCL_ONFAULT` | ✅ | ✅ | ✅ | |
| `MS_ASYNC` | ✅ | ✅ | ✅ | |
| `MS_SYNC` | ✅ | ✅ | ✅ | |
| `MS_INVALIDATE` | ✅ | ✅ | ✅ | |
| `MADV_NORMAL` | ✅ | ✅ | ✅ | |
| `MADV_RANDOM` | ✅ | ✅ | ✅ | |
| `MADV_SEQUENTIAL` | ✅ | ✅ | ✅ | |
| `MADV_WILLNEED` | ✅ | ✅ | ✅ | |
| `MADV_DONTNEED` | ✅ | ✅ | ✅ | |
| `MADV_FREE` | Linux | ✅ | ✅ | ✅ | |
| `MADV_REMOVE` | ✅ | ✅ | ✅ | |
| `MADV_DONTFORK` | ✅ | ✅ | ✅ | |
| `MADV_DOFORK` | ✅ | ✅ | ✅ | |
| `MADV_HWPOISON` | ✅ | ✅ | ✅ | |
| `MADV_MERGEABLE` | ✅ | ✅ | ✅ | |
| `MADV_UNMERGEABLE` | ✅ | ✅ | ✅ | |
| `MADV_SOFT_OFFLINE` | ✅ | ✅ | ✅ | |
| `MADV_HUGEPAGE` | ✅ | ✅ | ✅ | |
| `MADV_NOHUGEPAGE` | ✅ | ✅ | ✅ | |
| `MADV_DONTDUMP` | ✅ | ✅ | ✅ | |
| `MADV_DODUMP` | ✅ | ✅ | ✅ | |
| `MADV_POPULATE_READ` | ✅ | ✅ | ✅ | |
| `MADV_POPULATE_WRITE` | ✅ | ✅ | ✅ | |
| `MADV_COLD` | ✅ | ✅ | ✅ | |
| `MADV_PAGEOUT` | ✅ | ✅ | ✅ | |
| `MADV_COLLAPSE` | ✅ | ✅ | ✅ | |
| `POSIX_MADV_NORMAL` | ✅ | ✅ | ✅ | |
| `POSIX_MADV_SEQUENTIAL` | ✅ | ✅ | ✅ | |
| `POSIX_MADV_RANDOM` | ✅ | ✅ | ✅ | |
| `POSIX_MADV_WILLNEED` | ✅ | ✅ | ✅ | |
| `POSIX_MADV_DONTNEED` | ✅ | ✅ | ✅ | |
| `MFD_CLOEXEC` | ✅ | ✅ | ✅ | |
| `MFD_ALLOW_SEALING` | ✅ | ✅ | ✅ | |
| `MFD_HUGETLB` | ✅ | ✅ | ✅ | |
| `MFD_NOEXEC_SEAL` | ✅ | ✅ | ✅ | |
| `MFD_EXEC` | ✅ | ✅ | ✅ | |
| `MFD_SYNC` | ✅ | ✅ | ✅ | |
| `membarrier` | Linux | ✅ | ✅ | ✅ | |
| `userfaultfd` | Linux | ✅ | ✅ | ✅ | |

---

## 2.6 进程间通信 (IPC)

### `<sys/ipc.h>`, `<sys/msg.h>`, `<sys/sem.h>`, `<sys/shm.h>`

| 接口/宏 | glibc | musl | OHOS | 说明 |
|---------|:-----:|:----:|:----:|------|
| `ftok` | ✅ | ✅ | ✅ | |
| `msgget` | ✅ | ✅ | ✅ | |
| `msgsnd` | ✅ | ✅ | ✅ | |
| `msgrcv` | ✅ | ✅ | ✅ | |
| `msgctl` | ✅ | ✅ | ✅ | |
| `struct msqid_ds` | ✅ | ✅ | ✅ | |
| `semget` | ✅ | ✅ | ✅ | |
| `semop` | ✅ | ✅ | ✅ | |
| `semtimedop` | ✅ | ✅ | ✅ | |
| `semctl` | ✅ | ✅ | ✅ | |
| `struct semid_ds` | ✅ | ✅ | ✅ | |
| `union semun` | ✅ | ✅ | ✅ | |
| `shmget` | ✅ | ✅ | ✅ | |
| `shmat` | ✅ | ✅ | ✅ | |
| `shmdt` | ✅ | ✅ | ✅ | |
| `shmctl` | ✅ | ✅ | ✅ | |
| `struct shmid_ds` | ✅ | ✅ | ✅ | |
| `IPC_CREAT` | ✅ | ✅ | ✅ | |
| `IPC_EXCL` | ✅ | ✅ | ✅ | |
| `IPC_NOWAIT` | ✅ | ✅ | ✅ | |
| `IPC_RMID` | ✅ | ✅ | ✅ | |
| `IPC_SET` | ✅ | ✅ | ✅ | |
| `IPC_STAT` | ✅ | ✅ | ✅ | |
| `IPC_INFO` | ✅ | ✅ | ✅ | |
| `IPC_PRIVATE` | ✅ | ✅ | ✅ | |
| `SHM_RDONLY` | ✅ | ✅ | ✅ | |
| `SHM_RND` | ✅ | ✅ | ✅ | |
| `SHM_REMAP` | ✅ | ✅ | ✅ | |
| `SHM_HUGETLB` | ✅ | ✅ | ✅ | |
| `SHM_NORESERVE` | ✅ | ✅ | ✅ | |
| `SHM_LOCK` | ✅ | ✅ | ✅ | |
| `SHM_UNLOCK` | ✅ | ✅ | ✅ | |
| `GETPID` | ✅ | ✅ | ✅ | |
| `GETVAL` | ✅ | ✅ | ✅ | |
| `GETALL` | ✅ | ✅ | ✅ | |
| `SETVAL` | ✅ | ✅ | ✅ | |
| `SETALL` | ✅ | ✅ | ✅ | |
| `SEM_UNDO` | ✅ | ✅ | ✅ | |
| `SHMLBA` | ✅ | ✅ | ✅ | |

### `<mqueue.h>`

| 接口 | glibc | musl | OHOS | 说明 |
|------|:-----:|:----:|:----:|------|
| `mq_open` | ✅ | ✅ | ✅ | |
| `mq_close` | ✅ | ✅ | ✅ | |
| `mq_unlink` | ✅ | ✅ | ✅ | |
| `mq_send` | ✅ | ✅ | ✅ | |
| `mq_timedsend` | ✅ | ✅ | ✅ | |
| `mq_receive` | ✅ | ✅ | ✅ | |
| `mq_timedreceive` | ✅ | ✅ | ✅ | |
| `mq_notify` | ✅ | ✅ | ✅ | |
| `mq_getattr` | ✅ | ✅ | ✅ | |
| `mq_setattr` | ✅ | ✅ | ✅ | |
| `mqd_t` | ✅ | ✅ | ✅ | |
| `struct mq_attr` | ✅ | ✅ | ✅ | |

---

## 2.7 同步与 I/O 多路复用

### `<poll.h>`

| 接口/宏 | glibc | musl | OHOS | 说明 |
|---------|:-----:|:----:|:----:|------|
| `poll` | ✅ | ✅ | ✅ | |
| `ppoll` | ✅ | ✅ | ✅ | |
| `struct pollfd` | ✅ | ✅ | ✅ | |
| `POLLIN` | ✅ | ✅ | ✅ | |
| `POLLPRI` | ✅ | ✅ | ✅ | |
| `POLLOUT` | ✅ | ✅ | ✅ | |
| `POLLERR` | ✅ | ✅ | ✅ | |
| `POLLHUP` | ✅ | ✅ | ✅ | |
| `POLLNVAL` | ✅ | ✅ | ✅ | |
| `POLLRDNORM` | ✅ | ✅ | ✅ | |
| `POLLRDBAND` | ✅ | ✅ | ✅ | |
| `POLLWRNORM` | ✅ | ✅ | ✅ | |
| `POLLWRBAND` | ✅ | ✅ | ✅ | |
| `POLLFREE` | Linux | ✅ | ✅ | ✅ | |
| `POLL_BUSY_LOOP` | Linux | ✅ | ✅ | ✅ | |

### `<sys/select.h>` / `<sys/time.h>` / `<sys/epoll.h>`

| 接口/宏 | glibc | musl | OHOS | 说明 |
|---------|:-----:|:----:|:----:|------|
| `select` | ✅ | ✅ | ✅ | |
| `pselect` | ✅ | ✅ | ✅ | |
| `FD_CLR` | ✅ | ✅ | ✅ | |
| `FD_ISSET` | ✅ | ✅ | ✅ | |
| `FD_SET` | ✅ | ✅ | ✅ | |
| `FD_ZERO` | ✅ | ✅ | ✅ | |
| `fd_set` | ✅ | ✅ | ✅ | |
| `epoll_create` | ✅ | ✅ | ✅ | |
| `epoll_create1` | ✅ | ✅ | ✅ | |
| `epoll_ctl` | ✅ | ✅ | ✅ | |
| `epoll_wait` | ✅ | ✅ | ✅ | |
| `epoll_pwait` | ✅ | ✅ | ✅ | |
| `epoll_pwait2` | ✅ | ✅ | ✅ | |
| `struct epoll_event` | ✅ | ✅ | ✅ | |
| `EPOLLIN` | ✅ | ✅ | ✅ | |
| `EPOLLOUT` | ✅ | ✅ | ✅ | |
| `EPOLLPRI` | ✅ | ✅ | ✅ | |
| `EPOLLERR` | ✅ | ✅ | ✅ | |
| `EPOLLHUP` | ✅ | ✅ | ✅ | |
| `EPOLLRDHUP` | ✅ | ✅ | ✅ | |
| `EPOLLET` | ✅ | ✅ | ✅ | |
| `EPOLLONESHOT` | ✅ | ✅ | ✅ | |
| `EPOLLWAKEUP` | ✅ | ✅ | ✅ | |
| `EPOLL_CTL_ADD` | ✅ | ✅ | ✅ | |
| `EPOLL_CTL_MOD` | ✅ | ✅ | ✅ | |
| `EPOLL_CTL_DEL` | ✅ | ✅ | ✅ | |
| `eventfd` | ✅ | ✅ | ✅ | |
| `eventfd_read` | ✅ | ✅ | ✅ | |
| `eventfd_write` | ✅ | ✅ | ✅ | |
| `EFD_SEMAPHORE` | ✅ | ✅ | ✅ | |
| `EFD_CLOEXEC` | ✅ | ✅ | ✅ | |
| `EFD_NONBLOCK` | ✅ | ✅ | ✅ | |
| `timerfd_create` | ✅ | ✅ | ✅ | |
| `timerfd_gettime` | ✅ | ✅ | ✅ | |
| `timerfd_settime` | ✅ | ✅ | ✅ | |
| `TFD_CLOEXEC` | ✅ | ✅ | ✅ | |
| `TFD_NONBLOCK` | ✅ | ✅ | ✅ | |
| `TFD_TIMER_ABSTIME` | ✅ | ✅ | ✅ | |
| `TFD_TIMER_CANCEL_ON_SET` | ✅ | ✅ | ✅ | |
| `inotify_init` | ✅ | ✅ | ✅ | |
| `inotify_init1` | ✅ | ✅ | ✅ | |
| `inotify_add_watch` | ✅ | ✅ | ✅ | |
| `inotify_rm_watch` | ✅ | ✅ | ✅ | |
| `inotify_event` | ✅ | ✅ | ✅ | |
| `signalfd` | ✅ | ✅ | ✅ | |
| `SFD_NONBLOCK` | ✅ | ✅ | ✅ | |
| `SFD_CLOEXEC` | ✅ | ✅ | ✅ | |


---

## 2.8 正则表达式与模式匹配

### `<regex.h>`

| 接口/类型 | glibc | musl | OHOS | 说明 |
|-----------|:-----:|:----:|:----:|------|
| `regcomp` | ✅ | ✅ | ✅ | |
| `regexec` | ✅ | ✅ | ✅ | |
| `regfree` | ✅ | ✅ | ✅ | |
| `regerror` | ✅ | ✅ | ✅ | |
| `regex_t` | ✅ | ✅ | ✅ | |
| `regmatch_t` | ✅ | ✅ | ✅ | ⚠️ regoff_t 差异 |
| `regoff_t` | ✅ | ✅ | ✅ | ⚠️ glibc 64位仍为32-bit; musl 使用 ssize_t |
| `REG_EXTENDED` | ✅ | ✅ | ✅ | |
| `REG_ICASE` | ✅ | ✅ | ✅ | |
| `REG_NOSUB` | ✅ | ✅ | ✅ | |
| `REG_NEWLINE` | ✅ | ✅ | ✅ | |
| `REG_NOTBOL` | ✅ | ✅ | ✅ | |
| `REG_NOTEOL` | ✅ | ✅ | ✅ | |
| `REG_STARTEND` | ✅ | ❌ | ❌ | musl 不支持 |
| `REG_BACKTRACKING_MAX` | GNU | ✅ | ❌ | ❌ | |
| `REG_LITERAL` | GNU | ✅ | ❌ | ❌ | |
| `REG_PEND` | GNU | ✅ | ❌ | ❌ | |
| `REG_UCP` | GNU | ✅ | ❌ | ❌ | |
| `REG_UNGREEDY` | GNU | ✅ | ❌ | ❌ | |

### `<fnmatch.h>`

| 接口/宏 | glibc | musl | OHOS | 说明 |
|---------|:-----:|:----:|:----:|------|
| `fnmatch` | ✅ | ✅ | ✅ | |
| `FNM_PATHNAME` | ✅ | ✅ | ✅ | |
| `FNM_NOESCAPE` | ✅ | ✅ | ✅ | |
| `FNM_PERIOD` | ✅ | ✅ | ✅ | |
| `FNM_FILE_NAME` | ✅ | ✅ | ✅ | |
| `FNM_LEADING_DIR` | ✅ | ❌ | ❌ | |
| `FNM_CASEFOLD` | GNU | ✅ | ✅ | ✅ | |
| `FNM_EXTMATCH` | GNU | ✅ | ❌ | ❌ | |

### `<glob.h>`

| 接口/类型 | glibc | musl | OHOS | 说明 |
|-----------|:-----:|:----:|:----:|------|
| `glob` | ✅ | ✅ | ✅ | |
| `globfree` | ✅ | ✅ | ✅ | |
| `glob_t` | ✅ | ✅ | ✅ | |
| `GLOB_ERR` | ✅ | ✅ | ✅ | |
| `GLOB_MARK` | ✅ | ✅ | ✅ | |
| `GLOB_NOSORT` | ✅ | ✅ | ✅ | |
| `GLOB_DOOFFS` | ✅ | ✅ | ✅ | |
| `GLOB_NOCHECK` | ✅ | ✅ | ✅ | |
| `GLOB_APPEND` | ✅ | ✅ | ✅ | |
| `GLOB_NOESCAPE` | ✅ | ✅ | ✅ | |
| `GLOB_PERIOD` | ✅ | ✅ | ✅ | |
| `GLOB_TILDE` | GNU | ✅ | ❌ | ❌ | |
| `GLOB_TILDE_CHECK` | GNU | ✅ | ❌ | ❌ | |
| `GLOB_ONLYDIR` | GNU | ✅ | ❌ | ❌ | |
| `GLOB_BRACE` | GNU | ✅ | ❌ | ❌ | |
| `GLOB_NOMAGIC` | GNU | ✅ | ❌ | ❌ | |
| `GLOB_ALTDIRFUNC` | GNU | ✅ | ❌ | ❌ | |

---

## 2.9 国际化与字符集

### `<iconv.h>`

| 接口/类型 | glibc | musl | OHOS | 说明 |
|-----------|:-----:|:----:|:----:|------|
| `iconv_open` | ✅ | ✅ | ✅ | |
| `iconv` | ✅ | ✅ | ✅ | ⚠️ 不可转换字符处理不同 |
| `iconv_close` | ✅ | ✅ | ✅ | |
| `iconv_t` | ✅ | ✅ | ✅ | |

> **编码覆盖差异**：
> - glibc: ~200+ 编码（含 EUC-JP, Shift_JIS, GB18030, BIG5, KOI8-R 等）
> - musl: ~50-80 编码（主要覆盖 UTF-*, ISO-8859-*, ASCII, CP*, EBCDIC）
> - musl 缺少：GB18030 (有), Shift_JIS, EUC-JP, Big5, KOI8-U, TIS-620 等
> - musl 不支持 `//TRANSLIT` 后缀
> - musl 对无效输入替换为 '?' 而非返回 EILSEQ

### `<langinfo.h>`

| 接口/常量 | glibc | musl | OHOS | 说明 |
|-----------|:-----:|:----:|:----:|------|
| `nl_langinfo` | ✅ | ✅ | ✅ | |
| `nl_langinfo_l` | ✅ | ✅ | ✅ | |
| `CODESET` | ✅ | ✅ | ✅ | |
| `D_T_FMT` | ✅ | ✅ | ✅ | |
| `D_FMT` | ✅ | ✅ | ✅ | |
| `T_FMT` | ✅ | ✅ | ✅ | |
| `T_FMT_AMPM` | ✅ | ✅ | ✅ | |
| `AM_STR`/`PM_STR` | ✅ | ✅ | ✅ | |
| `DAY_1` ~ `DAY_7` | ✅ | ✅ | ✅ | |
| `ABDAY_1` ~ `ABDAY_7` | ✅ | ✅ | ✅ | |
| `MON_1` ~ `MON_12` | ✅ | ✅ | ✅ | |
| `ABMON_1` ~ `ABMON_12` | ✅ | ✅ | ✅ | |
| `ERA` | ✅ | ✅ | ✅ | |
| `ERA_D_T_FMT` | ✅ | ✅ | ✅ | |
| `ERA_D_FMT` | ✅ | ✅ | ✅ | |
| `ERA_T_FMT` | ✅ | ✅ | ✅ | |
| `ALT_DIGITS` | ✅ | ✅ | ✅ | |
| `RADIXCHAR` | ✅ | ✅ | ✅ | |
| `THOUSEP` | ✅ | ✅ | ✅ | |
| `YESEXPR` | ✅ | ✅ | ✅ | |
| `NOEXPR` | ✅ | ✅ | ✅ | |
| `CRNCYSTR` | ✅ | ✅ | ✅ | |
| `nl_item` | ✅ | ✅ | ✅ | |

### `<monetary.h>`

| 接口 | glibc | musl | OHOS | 说明 |
|------|:-----:|:----:|:----:|------|
| `strfmon` | ✅ | ✅ | ✅ | |
| `strfmon_l` | ✅ | ✅ | ✅ | |

---

## 2.10 搜索与排序

### `<search.h>`

| 接口/类型 | glibc | musl | OHOS | 说明 |
|-----------|:-----:|:----:|:----:|------|
| `hcreate` | ✅ | ✅ | ✅ | |
| `hdestroy` | ✅ | ✅ | ✅ | |
| `hsearch` | ✅ | ✅ | ✅ | |
| `hcreate_r` | GNU | ✅ | ✅ | ✅ | |
| `hdestroy_r` | GNU | ✅ | ✅ | ✅ | |
| `hsearch_r` | GNU | ✅ | ✅ | ✅ | |
| `tsearch` | ✅ | ✅ | ✅ | |
| `tfind` | ✅ | ✅ | ✅ | |
| `tdelete` | ✅ | ✅ | ✅ | |
| `twalk` | ✅ | ✅ | ✅ | |
| `tdestroy` | GNU | ✅ | ✅ | ✅ | |
| `lfind` | ✅ | ✅ | ✅ | |
| `lsearch` | ✅ | ✅ | ✅ | |
| `insque` | ✅ | ✅ | ✅ | |
| `remque` | ✅ | ✅ | ✅ | |
| `ENTRY` | ✅ | ✅ | ✅ | |
| `ACTION` | ✅ | ✅ | ✅ | |
| `VISIT` | ✅ | ✅ | ✅ | |

### `<stdlib.h>` 排序扩展

| 接口 | glibc | musl | OHOS | 说明 |
|------|:-----:|:----:|:----:|------|
| `qsort` | ✅ | ✅ | ✅ | |
| `qsort_r` (BSD) | ✅ | ✅ | ✅ | ⚠️ musl 使用 BSD 签名 |
| `qsort_r` (GNU) | ✅ | ❌ | ❌ | 签名不同，ABI 不兼容 |
| `qsort_s` (C11.K) | ✅ | ⚠️ | ⚠️ | 签名不同 |
| `bsearch` | ✅ | ✅ | ✅ | |
| `bsearch_r` | ✅ | ❌ | ❌ | |
| `heapsort` | BSD | ✅ | ✅ | ✅ | |
| `mergesort` | BSD | ✅ | ✅ | ✅ | |
| `radixsort` | BSD | ✅ | ❌ | ❌ | |

---

## 2.11 词法分析与终端控制

### `<wordexp.h>`

| 接口/类型 | glibc | musl | OHOS | 说明 |
|-----------|:-----:|:----:|:----:|------|
| `wordexp` | ✅ | ✅ | ✅ | |
| `wordfree` | ✅ | ✅ | ✅ | |
| `wordexp_t` | ✅ | ✅ | ✅ | |
| `WRDE_APPEND` | ✅ | ✅ | ✅ | |
| `WRDE_DOOFFS` | ✅ | ✅ | ✅ | |
| `WRDE_NOCMD` | ✅ | ✅ | ✅ | |
| `WRDE_REUSE` | ✅ | ✅ | ✅ | |
| `WRDE_SHOWERR` | ✅ | ✅ | ✅ | |
| `WRDE_UNDEF` | ✅ | ✅ | ✅ | |
| `WRDE_CMDSUB` | GNU | ✅ | ❌ | ❌ | |
| `WRDE_NOSPLIT` | GNU | ✅ | ❌ | ❌ | |

### `<termios.h>`

| 接口/宏 | glibc | musl | OHOS | 说明 |
|---------|:-----:|:----:|:----:|------|
| `tcgetattr` | ✅ | ✅ | ✅ | |
| `tcsetattr` | ✅ | ✅ | ✅ | |
| `tcsendbreak` | ✅ | ✅ | ✅ | |
| `tcdrain` | ✅ | ✅ | ✅ | |
| `tcflush` | ✅ | ✅ | ✅ | |
| `tcflow` | ✅ | ✅ | ✅ | |
| `cfmakeraw` | ✅ | ✅ | ✅ | |
| `cfgetispeed` | ✅ | ✅ | ✅ | |
| `cfgetospeed` | ✅ | ✅ | ✅ | |
| `cfsetispeed` | ✅ | ✅ | ✅ | |
| `cfsetospeed` | ✅ | ✅ | ✅ | |
| `cfsetspeed` | ✅ | ✅ | ✅ | |
| `tcgetsid` | ✅ | ✅ | ✅ | |
| `struct termios` | ✅ | ✅ | ✅ | |
| `B0` ~ `B460800` | ✅ | ✅ | ✅ | 波特率常量 |
| `CLOCAL` | ✅ | ✅ | ✅ | |
| `CREAD` | ✅ | ✅ | ✅ | |
| `CSIZE` | ✅ | ✅ | ✅ | |
| `CS5`/`CS6`/`CS7`/`CS8` | ✅ | ✅ | ✅ | |
| `CSTOPB` | ✅ | ✅ | ✅ | |
| `PARENB` | ✅ | ✅ | ✅ | |
| `PARODD` | ✅ | ✅ | ✅ | |
| `ECHO` | ✅ | ✅ | ✅ | |
| `ECHOE` | ✅ | ✅ | ✅ | |
| `ECHOK` | ✅ | ✅ | ✅ | |
| `ECHONL` | ✅ | ✅ | ✅ | |
| `ICANON` | ✅ | ✅ | ✅ | |
| `IEXTEN` | ✅ | ✅ | ✅ | |
| `ISIG` | ✅ | ✅ | ✅ | |
| `NOFLSH` | ✅ | ✅ | ✅ | |
| `TOSTOP` | ✅ | ✅ | ✅ | |
| `IGNBRK` | ✅ | ✅ | ✅ | |
| `BRKINT` | ✅ | ✅ | ✅ | |
| `IGNCR` | ✅ | ✅ | ✅ | |
| `ICRNL` | ✅ | ✅ | ✅ | |
| `INLCR` | ✅ | ✅ | ✅ | |
| `ISTRIP` | ✅ | ✅ | ✅ | |
| `IXON` | ✅ | ✅ | ✅ | |
| `IXOFF` | ✅ | ✅ | ✅ | |
| `OPOST` | ✅ | ✅ | ✅ | |
| `ONLCR` | ✅ | ✅ | ✅ | |
| `OCRNL` | ✅ | ✅ | ✅ | |
| `ONOCR` | ✅ | ✅ | ✅ | |
| `ONLRET` | ✅ | ✅ | ✅ | |
| `VMIN` | ✅ | ✅ | ✅ | |
| `VTIME` | ✅ | ✅ | ✅ | |
| `VERASE` | ✅ | ✅ | ✅ | |
| `VEOF` | ✅ | ✅ | ✅ | |
| `VINTR` | ✅ | ✅ | ✅ | |
| `VKILL` | ✅ | ✅ | ✅ | |
| `VQUIT` | ✅ | ✅ | ✅ | |
| `VSTART` | ✅ | ✅ | ✅ | |
| `VSTOP` | ✅ | ✅ | ✅ | |
| `VSUSP` | ✅ | ✅ | ✅ | |
| `VLNEXT` | ✅ | ✅ | ✅ | |
| `VWERASE` | ✅ | ✅ | ✅ | |
| `VEOL` | ✅ | ✅ | ✅ | |
| `VEOL2` | ✅ | ✅ | ✅ | |
| `VDISCARD` | ✅ | ✅ | ✅ | |
| `VREPRINT` | ✅ | ✅ | ✅ | |
| `FLUSHO` | ✅ | ✅ | ✅ | |
| `EXTPROC` | ✅ | ✅ | ✅ | |
| `TIOCGWINSZ` | ✅ | ✅ | ✅ | |
| `TIOCSWINSZ` | ✅ | ✅ | ✅ | |

---

## 2.12 异步 I/O 与其他 POSIX 接口

### `<aio.h>`

| 接口/类型 | glibc | musl | OHOS | 说明 |
|-----------|:-----:|:----:|:----:|------|
| `aio_read` | ✅ | ✅ | ✅ | musl 使用可取消版本 |
| `aio_write` | ✅ | ✅ | ✅ | |
| `aio_fsync` | ✅ | ✅ | ✅ | |
| `aio_error` | ✅ | ✅ | ✅ | |
| `aio_return` | ✅ | ✅ | ✅ | |
| `aio_suspend` | ✅ | ✅ | ✅ | |
| `aio_cancel` | ✅ | ✅ | ✅ | |
| `lio_listio` | ✅ | ✅ | ✅ | |
| `struct aiocb` | ✅ | ✅ | ✅ | |
| `AIO_ALLDONE` | ✅ | ✅ | ✅ | |
| `AIO_CANCELED` | ✅ | ✅ | ✅ | |
| `AIO_NOTCANCELED` | ✅ | ✅ | ✅ | |
| `LIO_NOP` | ✅ | ✅ | ✅ | |
| `LIO_NOWAIT` | ✅ | ✅ | ✅ | |
| `LIO_READ` | ✅ | ✅ | ✅ | |
| `LIO_WRITE` | ✅ | ✅ | ✅ | |

### `<syslog.h>`

| 接口/宏 | glibc | musl | OHOS | 说明 |
|---------|:-----:|:----:|:----:|------|
| `openlog` | ✅ | ✅ | ✅ | |
| `closelog` | ✅ | ✅ | ✅ | |
| `syslog` | ✅ | ✅ | ✅ | |
| `vsyslog` | ✅ | ✅ | ✅ | |
| `setlogmask` | ✅ | ✅ | ✅ | |
| `LOG_EMERG` | ✅ | ✅ | ✅ | |
| `LOG_ALERT` | ✅ | ✅ | ✅ | |
| `LOG_CRIT` | ✅ | ✅ | ✅ | |
| `LOG_ERR` | ✅ | ✅ | ✅ | |
| `LOG_WARNING` | ✅ | ✅ | ✅ | |
| `LOG_NOTICE` | ✅ | ✅ | ✅ | |
| `LOG_INFO` | ✅ | ✅ | ✅ | |
| `LOG_DEBUG` | ✅ | ✅ | ✅ | |
| `LOG_KERN` | ✅ | ✅ | ✅ | |
| `LOG_USER` | ✅ | ✅ | ✅ | |
| `LOG_MAIL` | ✅ | ✅ | ✅ | |
| `LOG_DAEMON` | ✅ | ✅ | ✅ | |
| `LOG_AUTH` | ✅ | ✅ | ✅ | |
| `LOG_SYSLOG` | ✅ | ✅ | ✅ | |
| `LOG_LPR` | ✅ | ✅ | ✅ | |
| `LOG_NEWS` | ✅ | ✅ | ✅ | |
| `LOG_UUCP` | ✅ | ✅ | ✅ | |
| `LOG_LOCAL0`~`LOG_LOCAL7` | ✅ | ✅ | ✅ | |
| `LOG_PID` | ✅ | ✅ | ✅ | |
| `LOG_CONS` | ✅ | ✅ | ✅ | |
| `LOG_NDELAY` | ✅ | ✅ | ✅ | |
| `LOG_ODELAY` | ✅ | ✅ | ✅ | |
| `LOG_NOWAIT` | ✅ | ✅ | ✅ | |

### `<ftw.h>`

| 接口 | glibc | musl | OHOS | 说明 |
|------|:-----:|:----:|:----:|------|
| `ftw` | ✅ | ✅ | ✅ | |
| `nftw` | ✅ | ✅ | ✅ | |
| `FTW_F` | ✅ | ✅ | ✅ | |
| `FTW_D` | ✅ | ✅ | ✅ | |
| `FTW_DNR` | ✅ | ✅ | ✅ | |
| `FTW_DP` | ✅ | ✅ | ✅ | |
| `FTW_NS` | ✅ | ✅ | ✅ | |
| `FTW_SL` | ✅ | ✅ | ✅ | |
| `FTW_SLN` | ✅ | ✅ | ✅ | |
| `FTW_PHYS` | ✅ | ✅ | ✅ | |
| `FTW_MOUNT` | ✅ | ✅ | ✅ | |
| `FTW_DEPTH` | ✅ | ✅ | ✅ | |
| `FTW_CHDIR` | ✅ | ✅ | ✅ | |

### `<sched.h>`

| 接口/宏 | glibc | musl | OHOS | 说明 |
|---------|:-----:|:----:|:----:|------|
| `sched_yield` | ✅ | ✅ | ✅ | |
| `sched_get_priority_max` | ✅ | ✅ | ✅ | |
| `sched_get_priority_min` | ✅ | ✅ | ✅ | |
| `sched_getparam` | ✅ | ✅ | ✅ | |
| `sched_setparam` | ✅ | ✅ | ✅ | |
| `sched_getscheduler` | ✅ | ✅ | ✅ | |
| `sched_setscheduler` | ✅ | ✅ | ✅ | |
| `sched_rr_get_interval` | ✅ | ✅ | ✅ | |
| `sched_getaffinity` | ✅ | ✅ | ✅ | |
| `sched_setaffinity` | ✅ | ✅ | ✅ | |
| `sched_getcpu` | ✅ | ✅ | ✅ | |
| `struct sched_param` | ✅ | ✅ | ✅ | |
| `SCHED_OTHER` | ✅ | ✅ | ✅ | |
| `SCHED_FIFO` | ✅ | ✅ | ✅ | |
| `SCHED_RR` | ✅ | ✅ | ✅ | |
| `SCHED_BATCH` | Linux | ✅ | ✅ | ✅ | |
| `SCHED_IDLE` | Linux | ✅ | ✅ | ✅ | |
| `SCHED_DEADLINE` | Linux | ✅ | ✅ | ✅ | |
| `SCHED_RESET_ON_FORK` | ✅ | ✅ | ✅ | |
| `CPU_SET` | ✅ | ✅ | ✅ | |
| `CPU_CLR` | ✅ | ✅ | ✅ | |
| `CPU_ISSET` | ✅ | ✅ | ✅ | |
| `CPU_ZERO` | ✅ | ✅ | ✅ | |
| `CPU_COUNT` | ✅ | ✅ | ✅ | |
| `CPU_AND` | ✅ | ✅ | ✅ | |
| `CPU_OR` | ✅ | ✅ | ✅ | |
| `CPU_XOR` | ✅ | ✅ | ✅ | |
| `CPU_EQUAL` | ✅ | ✅ | ✅ | |
| `cpu_set_t` | ✅ | ✅ | ✅ | |
| `clone` | ✅ | ⚠️ | ⚠️ | musl 有封装但需 _GNU_SOURCE |
| `unshare` | ✅ | ✅ | ✅ | |
| `setns` | ✅ | ✅ | ✅ | |

### `<semaphore.h>`

| 接口/类型 | glibc | musl | OHOS | 说明 |
|-----------|:-----:|:----:|:----:|------|
| `sem_init` | ✅ | ✅ | ✅ | |
| `sem_destroy` | ✅ | ✅ | ✅ | |
| `sem_wait` | ✅ | ✅ | ✅ | |
| `sem_timedwait` | ✅ | ✅ | ✅ | |
| `sem_trywait` | ✅ | ✅ | ✅ | |
| `sem_post` | ✅ | ✅ | ✅ | |
| `sem_open` | ✅ | ✅ | ✅ | |
| `sem_close` | ✅ | ✅ | ✅ | |
| `sem_unlink` | ✅ | ✅ | ✅ | |
| `sem_getvalue` | ✅ | ✅ | ✅ | |
| `sem_t` | ✅ | ✅ | ✅ | |

---

## 2.13 缺失/桩实现接口

### `<utmp.h>` / `<utmpx.h>` / `<lastlog.h>`

| 接口/类型 | glibc | musl | OHOS | 说明 |
|-----------|:-----:|:----:|:----:|------|
| `struct utmp` | ✅ | ✅ | ✅ | |
| `struct utmpx` | ✅ | ✅ | ✅ | |
| `setutent` | ✅ | ⚠️ | ⚠️ | musl 为桩实现 |
| `getutent` | ✅ | ⚠️ | ⚠️ | musl 为桩实现 |
| `endutent` | ✅ | ⚠️ | ⚠️ | musl 为桩实现 |
| `setutxent` | ✅ | ⚠️ | ⚠️ | musl 为桩实现 |
| `getutxent` | ✅ | ⚠️ | ⚠️ | musl 为桩实现 |
| `endutxent` | ✅ | ⚠️ | ⚠️ | musl 为桩实现 |
| `getutxid` | ✅ | ⚠️ | ⚠️ | musl 为桩实现 |
| `getutxline` | ✅ | ⚠️ | ⚠️ | musl 为桩实现 |
| `pututxline` | ✅ | ⚠️ | ⚠️ | musl 为桩实现 |
| `utmpxname` | ✅ | ⚠️ | ⚠️ | musl 为桩实现 |
| `updwtmp` | ✅ | ⚠️ | ⚠️ | musl 为桩实现 |
| `updwtmpx` | ✅ | ⚠️ | ⚠️ | musl 为桩实现 |
| `login` / `logout` | ✅ | ⚠️ | ⚠️ | musl 为桩实现 |
| `logwtmp` | ✅ | ⚠️ | ⚠️ | musl 为桩实现 |
| `struct lastlog` | ✅ | ⚠️ | ⚠️ | |

### `<fts.h>` — ⚠️ musl 完全不提供

| 接口 | glibc | musl | OHOS | 说明 |
|------|:-----:|:----:|:----:|------|
| `fts_open` | ✅ | ❌ | ❌ | glibc ABI 有 bug |
| `fts_read` | ✅ | ❌ | ❌ | |
| `fts_children` | ✅ | ❌ | ❌ | |
| `fts_close` | ✅ | ❌ | ❌ | |
| `fts_set` | ✅ | ❌ | ❌ | |
| `FTSENT` | ✅ | ❌ | ❌ | |
| `FTS_*` 常量 | ✅ | ❌ | ❌ | |

> **注意**: fts.h 虽然在 glibc 中存在，但 musl 作者认为其 ABI 设计有 bug 不愿实现。需要 fts 的软件可以使用独立的 fts 便携库或 nftw 替代。

### `<shadow.h>`

| 接口 | glibc | musl | OHOS | 说明 |
|------|:-----:|:----:|:----:|------|
| `setspent` | ✅ | ✅ | ✅ | |
| `endspent` | ✅ | ✅ | ✅ | |
| `getspent` | ✅ | ✅ | ✅ | |
| `getspnam` | ✅ | ✅ | ✅ | |
| `struct spwd` | ✅ | ✅ | ✅ | |
| `lckpwdf` | ✅ | ❌ | ❌ | |
| `ulckpwdf` | ✅ | ❌ | ❌ | |
| `sgetspent` | ✅ | ❌ | ❌ | |
| `fgetspent` | ✅ | ❌ | ❌ | |
| `putspent` | ✅ | ❌ | ❌ | |

---

## 2.14 动态加载接口

### `<dlfcn.h>`

| 接口/宏 | glibc | musl | OHOS | 说明 |
|---------|:-----:|:----:|:----:|------|
| `dlopen` | ✅ | ✅ | ✅ | |
| `dlclose` | ✅ | ✅ | ✅ | ⚠️ musl 为空操作 |
| `dlsym` | ✅ | ✅ | ✅ | |
| `dlerror` | ✅ | ✅ | ✅ | |
| `dlvsym` | ✅ | ✅ | ✅ | |
| `dladdr` | ✅ | ✅ | ✅ | |
| `dlinfo` | ✅ | ✅ | ✅ | |
| `dl_iterate_phdr` | ✅ | ✅ | ✅ | |
| `RTLD_LAZY` | ✅ | ✅ | ✅ | ⚠️ musl BIND_NOW 下效果不同 |
| `RTLD_NOW` | ✅ | ✅ | ✅ | |
| `RTLD_GLOBAL` | ✅ | ✅ | ✅ | |
| `RTLD_LOCAL` | ✅ | ✅ | ✅ | |
| `RTLD_DEFAULT` | ✅ | ✅ | ✅ | |
| `RTLD_NEXT` | ✅ | ✅ | ✅ | |
| `RTLD_NODELETE` | ✅ | ✅ | ✅ | |
| `RTLD_NOLOAD` | ✅ | ✅ | ✅ | |
| `RTLD_DEEPBIND` | ✅ | ❌ | ❌ | musl 不支持 |
| `RTLD_DI_LINKMAP` | ✅ | ✅ | ✅ | |
| `RTLD_DI_ORIGIN` | ✅ | ✅ | ✅ | |
| `dlopen_ns_ext` | ❌ | ❌ | ✅ | OHOS 命名空间隔离 |

> **关键差异**: 
> 1. `dlclose`: musl 是空操作（从不卸载共享库），glibc 有引用计数卸载
> 2. `RTLD_DEEPBIND`: musl 不支持
> 3. BIND_NOW: musl 默认 BIND_NOW，影响扩展模块加载
> 4. 符号版本：musl 不使用 symbol versioning

---

## 2.15 统计汇总

### 按标准的接口覆盖统计

| 标准层级 | glibc | musl | OHOS musl | 说明 |
|----------|:-----:|:----:|:---------:|------|
| ISO C89/C90 (~350 接口) | 100% | ~100% | ~100% | 差异可忽略 |
| ISO C99 (+~200 接口) | 100% | ~100% | ~100% | 几乎无差异 |
| ISO C11 (+~80 接口) | ~99% | ~99% | ~99% | |
| ISO C17/C23 (+~40 接口) | ~95% | ~70% | ~70% | musl 未跟进 `_s` 安全函数 |
| POSIX.1 Base (~500 接口) | ~100% | ~97% | ~97% | fts.h 是主要缺失 |
| POSIX.1 Options (~200 接口) | ~95% | ~85% | ~90% | OHOS 补强了部分 |
| **综合估算** | **~100%** | **~92%** | **~93%** | |

### musl 完全不支持的接口清单

| 头文件 | 接口 | 类别 | 影响 |
|--------|------|------|:----:|
| `<fts.h>` | fts_open/read/children/close/set | 全部 | 中 |
| `<error.h>` | error/error_at_line | 全部 | 中 |
| `<argp.h>` | argp_parse 全部 | 全部 | 中 |
| `<obstack.h>` | obstack 全部 | 全部 | 低 |
| `<execinfo.h>` | backtrace 全部 | 全部 | 中 |
| `<printf.h>` | register_printf_* | 全部 | 低 |
| `<makecontext.h>` | makecontext/swapcontext | 全部 | 低 |
| `<encrypt.h>` | encrypt | 全部 | 低 |
| `<stdlib.h>` | fcloseall | GNU | 低 |
| `<stdlib.h>` | memfrob | GNU | 低 |
| `<stdlib.h>` | getloadavg | GNU | 中 |
| `<stdlib.h>` | basename(GNU版) | GNU | 高 |
| `<string.h>` | rawmemchr | GNU | 低 |
| `<string.h>` | strndupa/strdupa | GNU | 低 |
| `<string.h>` | inet_ntop_r | GNU | 低 |
| C11 Annex K | 所有 `_s` 后缀函数 | 全部 | 中 |
| `<dlfcn.h>` | RTLD_DEEPBIND | 选项 | 低 |
| `<math.h>` | clog10 | GNU | 低 |
| `<fenv.h>` | FE_NOMASK_ENV/feenableexcept | GNU | 低 |
| `<netdb.h>` | AI_IDN/NI_IDN 系列 | GNU | 低 |
| `<glob.h>` | GLOB_TILDE/GLOB_BRACE 等 | GNU | 中 |
| `<fnmatch.h>` | FNM_EXTMATCH/FNM_LEADING_DIR | GNU | 低 |
| `<regex.h>` | REG_STARTEND/REG_UCP 等 | GNU | 低 |
| `<pthread.h>` | set/getconcurrency/tryjoin_np | XSI | 低 |

---

*文档结束。最后更新：2026-03-23*

