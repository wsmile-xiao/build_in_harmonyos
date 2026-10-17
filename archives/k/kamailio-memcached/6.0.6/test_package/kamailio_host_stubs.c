/*
 * test_package/kamailio_host_stubs.c
 *
 * Kamailio core ABI stubs — a stand-in for the host application.
 *
 * A Kamailio module is a dlopen() plugin: `memcached.so` deliberately keeps
 * the Kamailio core API undefined and gets it from the running Kamailio
 * binary.  On OHOS (musl) there is no lazy binding for dynamically loaded
 * objects — *every* relocation is resolved before the object is returned
 * from dlopen().  A bare process therefore cannot load the module at all:
 *
 *     dlopen(memcached.so, RTLD_LAZY):
 *       Error relocating ...: pv_get_null: symbol not found
 *
 * To exercise the packaged module the way the real host does, the harness
 * defines the 21 Kamailio core symbols that the module imports and exports
 * them with -rdynamic (the same shape as the Kamailio binary, which is
 * linked -Wl,-export-dynamic).  None of these stubs is ever executed by the
 * checks in test_memcached_module.c; they exist so that relocation of the
 * module's own interface tables and of its embedded libmemcached code can
 * complete.
 *
 * Symbol inventory (nm -u memcached.so) split into
 *   * OHOS system runtime: libc.so / libc++_shared.so / libgcc — provided by
 *     the platform, 65 symbols;
 *   * Kamailio core ABI — the 21 symbols defined below.
 */

#include <stddef.h>

/* ── data objects exported by the Kamailio core ───────────────────── */
int log_stderr = 0;
int log_color = 0;
int process_no = 0;
void *log_prefix_val = 0;
void *_km_log_func = 0;
void *_ksr_slog_func = 0;

/* struct sr_pkg_api_t / struct log_level_info are opaque here: only their
 * addresses are relocated, no stub is executed.  Oversized byte arrays keep
 * them safely addressable. */
char _pkg_root[256] = {0};
char log_level_info[512] = {0};
char ut_buf_int2str[64] = {0};

/* ── core functions imported by the module ────────────────────────── */
int my_pid(void)
{
	return 0;
}

void MD5StringArray(char *dst, void *src, int size)
{
	(void)dst;
	(void)src;
	(void)size;
}

void dprint_color(int level)
{
	(void)level;
}

void dprint_color_reset(void)
{
}

void dprint_crit(const char *fmt, ...)
{
	(void)fmt;
}

int get_debug_level(char *mname, int mnlen)
{
	(void)mname;
	(void)mnlen;
	return 0;
}

int get_debug_facility(char *mname, int mnlen)
{
	(void)mname;
	(void)mnlen;
	return 0;
}

void *pv_get_buffer(void)
{
	return 0;
}

int pv_get_buffer_size(void)
{
	return 0;
}

int pv_get_null(void *msg, void *param, void *res)
{
	(void)msg;
	(void)param;
	(void)res;
	return 0;
}

int pv_parse_format(void *in, void *el)
{
	(void)in;
	(void)el;
	return 0;
}

int pv_printf_s(void *msg, void *list, void *s)
{
	(void)msg;
	(void)list;
	(void)s;
	return 0;
}
