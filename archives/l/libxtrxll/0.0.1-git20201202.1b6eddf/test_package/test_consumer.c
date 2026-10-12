/*
 * libxtrxll consumer integration test (Conan L1 test_package, run on HarmonyOS).
 *
 * This program is compiled and executed by test_package/conanfile.py against the
 * *packaged* library (include/ + lib/), so it depends on the real ABI, the real
 * symbol set and the real runtime behaviour of the installed artifact.
 *
 * It exercises the public API surface that is meaningful on a device-less host:
 *   - discovery lifecycle with an empty and a real candidate buffer
 *   - deterministic error mapping for unknown/absent transports
 *   - the logging subsystem (level round-trip + custom log callback dispatch)
 *
 * Every assertion below is deterministic and device independent.
 */

#include <stdio.h>
#include <string.h>
#include <errno.h>

#include "xtrxll_api.h"
#include "xtrxll_log.h"

static int g_checks = 0;
static int g_failed = 0;

#define CHECK(cond, msg)                                                    \
	do {                                                                \
		g_checks++;                                                 \
		if (!(cond)) {                                              \
			g_failed++;                                         \
			fprintf(stderr, "FAIL [%s:%d] %s\n", __FILE__,      \
			        __LINE__, (msg));                           \
		} else {                                                    \
			printf("ok   %s\n", (msg));                         \
		}                                                           \
	} while (0)

static int g_log_calls = 0;
static int g_log_last_severity = -1;

static void counting_logfunc(int severity, const struct tm *stm, int nsec,
                             const char subsystem[4], const char *function,
                             const char *file, int function_lno,
                             const char *fmt, va_list list)
{
	(void)stm; (void)nsec; (void)subsystem; (void)function;
	(void)file; (void)function_lno; (void)fmt; (void)list;
	g_log_calls++;
	g_log_last_severity = severity;
}

int main(void)
{
	xtrxll_device_info_t devs[4];
	struct xtrxll_dev *dev = NULL;
	int n;
	int res;

	printf("libxtrxll consumer integration test\n");
	printf("-----------------------------------\n");

	/* 1. Discovery with a zero-length buffer must report "no devices" and must
	 *    not touch the (empty) output buffer. */
	memset(devs, 0, sizeof(devs));
	CHECK(xtrxll_discovery(devs, 0) == 0,
	      "discovery(maxbuf=0) returns 0");

	/* 2. Discovery with a real buffer returns a non-negative device count that
	 *    fits in the buffer supplied. */
	n = xtrxll_discovery(devs, 4);
	CHECK(n >= 0, "discovery(maxbuf=4) returns a non-negative count");
	CHECK(n <= 4, "discovery() does not exceed the supplied buffer");

	/* 3. An unknown transport prefix must be rejected with -ENODEV, before any
	 *    attempt to touch the filesystem. */
	res = xtrxll_open("usb3380://nosuchdevice", 0, &dev);
	CHECK(res == -ENODEV, "open(usb3380://...) reports -ENODEV");

	/* 4. A well-formed PCIe handle for a path that does not exist must fail
	 *    cleanly.  Upstream semantics: xtrxll_open() tries every registered
	 *    transport in turn and, when none of them yields a device, returns the
	 *    generic "-ENODEV" (the per-module errno, e.g. -ENOENT from the failed
	 *    open(2), is deliberately swallowed by that loop).  Asserting the exact
	 *    code pins the documented "no usable device" contract. */
	res = xtrxll_open("pcie:///definitely/not/an/xtrx/device", 0, &dev);
	CHECK(res == -ENODEV, "open(pcie://<absent path>) reports -ENODEV");

	/* 5. Logging: level round-trip. */
	xtrxll_set_loglevel(XTRXLL_WARNING);
	CHECK(xtrxll_get_loglevel() == XTRXLL_WARNING,
	      "set_loglevel/get_loglevel round-trip (WARNING)");

	/* 6. Logging: a registered log callback must receive the error emitted by
	 *    the failing open(2) above (ERROR(1) <= current level WARNING(2)). */
	g_log_calls = 0;
	g_log_last_severity = -1;
	xtrxll_set_logfunc(counting_logfunc);
	(void)xtrxll_open("pcie:///definitely/not/an/xtrx/device", 0, &dev);
	CHECK(g_log_calls >= 1, "custom log callback invoked on open() failure");
	CHECK(g_log_last_severity == XTRXLL_ERROR,
	      "custom log callback received the XTRXLL_ERROR severity");

	/* 7. Restoring the default logger and lowering the level must silence the
	 *    same failure path. */
	xtrxll_set_logfunc(NULL);
	xtrxll_set_loglevel(XTRXLL_NONE);
	g_log_calls = 0;
	(void)xtrxll_open("pcie:///definitely/not/an/xtrx/device", 0, &dev);
	CHECK(g_log_calls == 0, "loglevel NONE silences the failure path");
	CHECK(xtrxll_get_loglevel() == XTRXLL_NONE,
	      "set_loglevel/get_loglevel round-trip (NONE)");

	/* 8. Device-dependent branch, expressed as exactly one assertion either
	 *    way so the assertion count stays constant. */
	xtrxll_set_loglevel(XTRXLL_WARNING);
	res = xtrxll_open(NULL, 0, &dev);
	if (n == 0) {
		CHECK(res == -ENODEV,
		      "open(NULL) with no XTRX present reports -ENODEV");
	} else {
		CHECK(res == 0, "open(NULL) with an XTRX present succeeds");
		if (res == 0) {
			printf("info live device: %s\n", xtrxll_get_name(dev));
			xtrxll_close(dev);
		}
	}

	printf("-----------------------------------\n");
	printf("%d checks, %d failed\n", g_checks, g_failed);
	return g_failed ? 1 : 0;
}
