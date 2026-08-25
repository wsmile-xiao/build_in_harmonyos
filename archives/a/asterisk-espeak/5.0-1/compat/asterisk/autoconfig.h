/* compat/asterisk/autoconfig.h — minimal generated config for HarmonyOS
 * 由 asterisk-22.5.0 的 autoconfig.h.in 模板生成（configure 产物替代）。
 * 鸿蒙 PC (aarch64/OHOS, clang) 平台配置：大多数宏留空，按需定义。
 * 生成自 autoconfig.h.in 的 #undef 模板 + 鸿蒙特定值。
 */
#ifndef ASTERISK_AUTOCONFIG_H
#define ASTERISK_AUTOCONFIG_H

#include "asterisk/buildopts.h"

/* 平台基础宏（鸿蒙 = Linux 类） */
/* json.h 需要：Define to 'long' or 'long long' */
#define AST_JSON_INT_T long long
/* select.h 需要：fd_set.fds_bits 的类型与大小（aarch64 unsigned long=8） */
#define TYPEOF_FD_SET_FDS_BITS unsigned long
#define SIZEOF_FD_SET_FDS_BITS 8
/* lock.h 需要：C11 原子（鸿蒙 clang 支持 __atomic 内建） */
#define HAVE_C_ATOMICS 1
#define HAVE_UNISTD_H 1
#define HAVE_STDINT_H 1
#define HAVE_INTTYPES_H 1
#define HAVE_STDDEF_H 1
#define HAVE_SYS_TYPES_H 1
#define HAVE_SYS_STAT_H 1
#define HAVE_SYS_TIME_H 1
#define HAVE_SYS_SELECT_H 1
#define HAVE_SYS_IOCTL_H 1
#define HAVE_SYS_MMAN_H 1
#define HAVE_FCNTL_H 1
#define HAVE_ERRNO_H 1
#define HAVE_LIMITS_H 1
#define HAVE_PTHREAD_H 1
#define HAVE_SEMAPHORE_H 1
#define HAVE_STRING_H 1
#define HAVE_STRINGS_H 1
#define HAVE_STDLIB_H 1
#define HAVE_MATH_H 1
#define HAVE_NETINET_IN_H 1
#define HAVE_ARPA_INET_H 1
#define HAVE_SYS_SOCKET_H 1
#define HAVE_NETDB_H 1
#define HAVE_SYSLOG_H 1
#define HAVE_SYS_UN_H 1

/* 常用函数 */
#define HAVE_SNPRINTF 1
#define HAVE_VSNPRINTF 1
#define HAVE_STRDUP 1
#define HAVE_SBRK 1
#define HAVE_SETSID 1
#define HAVE_USLEEP 1
#define HAVE_NANOSLEEP 1
#define HAVE_GETTIMEOFDAY 1
#define HAVE_CLOCK_GETTIME 1
#define HAVE_PTHREAD_MUTEX_TIMEDLOCK 1
#define HAVE_SEM_TIMEDWAIT 1
#define HAVE_GETHOSTBYNAME 1
#define HAVE_GETIFADDRS 1

/* 音频/语音相关（espeak 模块需要） */
#define HAVE_PORTAUDIO 1

/* 未支持的特性留空 */
#undef HAVE_LIBXML2
#undef HAVE_JACK
#undef HAVE_ALSA
#undef HAVE_OSS
#undef HAVE_PWLIB
#undef HAVE_OPENR2
#undef HAVE_GTK2

#endif /* ASTERISK_AUTOCONFIG_H */
