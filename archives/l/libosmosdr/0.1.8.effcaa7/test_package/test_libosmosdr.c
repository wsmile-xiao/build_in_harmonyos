/*
 * Consumer tests for libosmosdr on HarmonyOS / OpenHarmony PC (aarch64).
 *
 * Upstream libosmosdr ships no test suite at all: the source tree contains no
 * tests/ directory, no enable_testing()/add_test() call and no check/ctest
 * target. Every assertion below therefore belongs to the OHOS adaptation.
 */
#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include <osmosdr.h>

#ifndef TEST_EXPECT_SHARED
#define TEST_EXPECT_SHARED 1
#endif

static int g_checks;
static int g_failures;

static void check(int condition, const char *what)
{
	g_checks++;

	if (condition) {
		printf("  [PASS] %s\n", what);
	} else {
		g_failures++;
		printf("  [FAIL] %s\n", what);
	}
}

/*
 * TC-01 - the public library is linked and device enumeration is safe on a host
 * that has no OsmoSDR hardware attached.
 */
static void test_device_enumeration(void)
{
	uint32_t count;
	const char *name;

	printf("TC-01 device enumeration\n");

	count = osmosdr_get_device_count();
	printf("       osmosdr_get_device_count() = %u\n", count);
	check(count == 0,
	      "no OsmoSDR device is reported on a worker without hardware");

	name = osmosdr_get_device_name(0);
	check(name != NULL, "osmosdr_get_device_name() returns a valid pointer");
	check(name != NULL && name[0] == '\0',
	      "an unknown device index yields an empty name instead of a crash");
}

/*
 * TC-02 - the documented error contract for out-of-range and absent devices.
 * The library must fail gracefully instead of dereferencing a device that is
 * not present.
 */
static void test_error_contract(void)
{
	osmosdr_dev_t *dev = NULL;
	char manufact[256] = { 0 };
	char product[256] = { 0 };
	char serial[256] = { 0 };
	int r;

	printf("TC-02 error contract without hardware\n");

	r = osmosdr_get_device_usb_strings(0, manufact, product, serial);
	printf("       osmosdr_get_device_usb_strings() = %d\n", r);
	check(r < 0, "usb strings for a missing device report an error");

	r = osmosdr_open(&dev, 0);
	printf("       osmosdr_open() = %d\n", r);
	check(r != 0, "opening a missing device fails");
	check(dev == NULL, "a failed open leaves the device handle untouched");

	r = osmosdr_close(NULL);
	check(r != 0, "closing a NULL handle is rejected instead of crashing");
}

/*
 * TC-03 (OHOS specific) - the packaged shared object must be loadable by the
 * OHOS musl loader with all of its entry points resolvable. This is exactly the
 * failure mode the OHOS adaptation has to guard against: a .so whose dependency
 * chain (libusb-1.0.so) cannot be resolved at runtime.
 */
static void test_shared_object_loadable(void)
{
	static const char *symbols[] = {
		"osmosdr_get_device_count",
		"osmosdr_get_device_name",
		"osmosdr_get_device_usb_strings",
		"osmosdr_open",
		"osmosdr_close",
	};
	void *handle;
	const char *error;
	unsigned int i;

	printf("TC-03 OHOS shared object loadability\n");

	handle = dlopen("libosmosdr.so", RTLD_NOW | RTLD_LOCAL);
	if (handle == NULL) {
		error = dlerror();

		if (TEST_EXPECT_SHARED) {
			printf("       dlopen failed: %s\n",
			       error ? error : "unknown error");
			check(0, "libosmosdr.so resolves its dependencies at load time");
		} else {
			printf("       static package, dlopen skipped: %s\n",
			       error ? error : "not found");
		}

		return;
	}

	for (i = 0; i < sizeof(symbols) / sizeof(symbols[0]); i++)
		check(dlsym(handle, symbols[i]) != NULL, symbols[i]);

	dlclose(handle);
}

int main(void)
{
	/* Keep stdout unbuffered: when the build log is a pipe, a buffered
	 * stdio would swallow the test progress if a library call dies, which
	 * makes the failure location impossible to see from CI output. */
	setvbuf(stdout, NULL, _IONBF, 0);

	printf("libosmosdr consumer tests (HarmonyOS PC aarch64)\n");

	test_device_enumeration();
	test_error_contract();
	test_shared_object_loadable();

	printf("%d checks, %d failure(s)\n", g_checks, g_failures);

	return g_failures == 0 ? 0 : 1;
}
