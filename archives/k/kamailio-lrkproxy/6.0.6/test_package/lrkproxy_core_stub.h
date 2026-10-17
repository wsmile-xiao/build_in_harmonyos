/* kamailio core 符号 shim 头 —— 见 lrkproxy_core_stub.c 注释。 */
#ifndef LRKPROXY_CORE_STUB_H
#define LRKPROXY_CORE_STUB_H

#include <stddef.h>

typedef unsigned int ticks_t;

/* 内存分配器（真实语义实现） */
void *pkg_malloc(size_t s);
void *pkg_mallocz(size_t s);
void *shm_malloc(size_t s);
void *shm_mallocz(size_t s);
void pkg_free(void *p);
void shm_free(void *p);
void *pkg_realloc(void *p, size_t s);
void *pkg_reallocxf(void *p, size_t s);

/* 日志（抑制） */
int get_debug_level(void);
int get_debug_facility(void);
void _km_log_func(int level, const char *fmt, ...);
void _ksr_slog_func(int level, const char *fmt, ...);
void dprint_crit(void *log_info, const char *fmt, ...);

#endif /* LRKPROXY_CORE_STUB_H */
