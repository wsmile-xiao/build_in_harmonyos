/*
 * C API consumer test — bctbx_list + logging handler round-trip.
 */
#include <bctoolbox/list.h>
#include <bctoolbox/logging.h>

#include <stdarg.h>
#include <stdio.h>
#include <string.h>

static int g_log_hits = 0;
static int g_failures = 0;

static void my_log(const char *domain, BctbxLogLevel lvl, const char *fmt, va_list args) {
	(void)domain;
	(void)lvl;
	(void)fmt;
	(void)args;
	g_log_hits++;
}

static void check(int cond, const char *name) {
	printf("[test] %s: %s\n", name, cond ? "PASS" : "FAIL");
	if (!cond)
		g_failures++;
}

static void emit_log(const char *fmt, ...) {
	va_list ap;
	va_start(ap, fmt);
	bctbx_logv("test_package", BCTBX_LOG_MESSAGE, fmt, ap);
	va_end(ap);
}

int main(void) {
	/* bctbx_list core operations */
	bctbx_list_t *l = bctbx_list_append(NULL, (void *)"world");
	l = bctbx_list_prepend(l, (void *)"hello");
	check(bctbx_list_size(l) == 2u, "bctbx_list_size");
	check(strcmp((const char *)bctbx_list_nth_data(l, 0), "hello") == 0, "bctbx_list_nth_data");
	bctbx_list_free(l);

	/* logging: install handler then emit one message through bctbx_logv */
	bctbx_init_logger(TRUE);
	bctbx_set_log_level("test_package", BCTBX_LOG_MESSAGE);
	bctbx_set_log_handler(my_log);
	emit_log("consumer log round-trip");
	bctbx_logv_flush();
	check(g_log_hits >= 1, "bctbx logging handler");
	bctbx_uninit_logger();

	printf("%s\n", g_failures == 0 ? "ALL C TESTS PASSED" : "C TESTS FAILED");
	return g_failures == 0 ? 0 : 1;
}
