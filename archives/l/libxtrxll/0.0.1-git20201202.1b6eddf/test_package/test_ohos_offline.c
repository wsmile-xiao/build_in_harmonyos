/*
 * libxtrxll HarmonyOS-specific test (Conan L1 test_package, run on HarmonyOS).
 *
 * This program pins the two properties that the HarmonyOS adaptation of
 * libxtrxll actually changes, so a regression in either one fails the build:
 *
 *  1. Static plugin registration (XTRXLL_STATIC=ON)
 *     Upstream can build the transports as *dynamic* plugins that the core
 *     library locates with dlopen("libxtrxll_pcie.so.0").  That lookup depends
 *     on the loader search path (RPATH), which is fragile inside the Conan
 *     package layout.  Our recipe keeps the upstream default static linkage, so
 *     the PCIe transport object code is compiled *into* libxtrxll.so.
 *
 *     Observable consequence: the transport entry point exported by the plugin
 *     translation unit (xtrxllpciev0_init) is resolvable as a symbol of the
 *     linked library.  With dynamic plugins that symbol would live only in the
 *     separately-loaded .so and would not be visible here.  The symbol is
 *     therefore resolved through the dynamic linker and must be non-NULL.
 *
 *  2. Operation without the XTRX kernel driver
 *     The XTRX PCIe transport talks to /sys/class/xtrx/ and /dev/xtrx*.  On a
 *     HarmonyOS host without the XTRX board those are absent; discovery must
 *     report "no devices" cleanly (a non-negative count, zero here) and the
 *     library must not abort or leak file descriptors.  This is the exact
 *     environment the package is consumed in.
 *
 * Every assertion below is deterministic and device independent.
 */

#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
#include <dlfcn.h>

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

/* Number of open file descriptors of this process.  Used to prove that the
 * device-less error paths do not leak descriptors on HarmonyOS. */
static int count_open_fds(void)
{
	int n = 0;
	char path[64];
	for (int fd = 0; fd < 256; fd++) {
		snprintf(path, sizeof(path), "/proc/self/fd/%d", fd);
		if (access(path, F_OK) == 0)
			n++;
	}
	return n;
}

int main(void)
{
	xtrxll_device_info_t devs[4];
	struct xtrxll_dev *dev = NULL;
	int fds_before;
	int fds_after;
	int res;

	printf("libxtrxll HarmonyOS-specific test\n");
	printf("---------------------------------\n");

	xtrxll_set_loglevel(XTRXLL_ERROR);

	/* 1. Static plugin registration: the PCIe transport entry point must be a
	 *    symbol of the linked library (XTRXLL_STATIC compiles it into
	 *    libxtrxll.so instead of dlopen()ing a sibling plugin). */
	CHECK(dlsym(RTLD_DEFAULT, "xtrxllpciev0_init") != NULL,
	      "PCIe transport is linked into libxtrxll (XTRXLL_STATIC)");

	/* 2. Sanity: the core entry point is resolvable as well, i.e. the test
	 *    really is bound to the packaged library. */
	CHECK(dlsym(RTLD_DEFAULT, "xtrxll_open") != NULL,
	      "core entry point xtrxll_open is exported by the package");

	/* 3. The HarmonyOS toolchain reports CMAKE_SYSTEM_NAME=HarmonyOS, for which
	 *    upstream does not add -fPIC to the static plugin targets.  If the
	 *    recipe did not force CMAKE_POSITION_INDEPENDENT_CODE, the link of
	 *    libxtrxll.so would have failed; reaching this point proves the library
	 *    loaded successfully with the plugin code folded in. */
	CHECK(xtrxll_discovery(devs, 4) >= 0,
	      "library with folded-in plugin loads and runs");

	/* 4. Clean discovery without the XTRX kernel driver loaded. */
	fds_before = count_open_fds();
	res = xtrxll_discovery(devs, 4);
	CHECK(res >= 0, "discovery without the XTRX driver reports no error");
	CHECK(res == 0, "discovery reports 0 devices when no XTRX is present");

	/* 5. Repeated discovery is stable and idempotent (no state corruption in
	 *    the logging/transport bootstrap). */
	res = xtrxll_discovery(devs, 4);
	CHECK(res == 0, "repeated discovery stays clean and returns 0");

	/* 6. Failed transport opens must not leak file descriptors. */
	(void)xtrxll_open("pcie:///ohos/xtrx/absent", 0, &dev);
	(void)xtrxll_open(NULL, 0, &dev);
	fds_after = count_open_fds();
	CHECK(fds_after <= fds_before,
	      "failed transport opens do not leak file descriptors");

	printf("---------------------------------\n");
	printf("%d checks, %d failed\n", g_checks, g_failed);
	return g_failed ? 1 : 0;
}
