/* tslib consumer test — links against the packaged shared library and
 * asserts real API behaviour that does not require touchscreen hardware:
 * the version API contract and the clean failure path of ts_open().
 */
#include <stdio.h>
#include <string.h>
#include <tslib.h>

int main(void)
{
	struct ts_lib_version_data *ver = ts_libversion();

	if (ver == NULL) {
		fprintf(stderr, "FAIL: ts_libversion() returned NULL\n");
		return 1;
	}
	if (ver->package_version == NULL ||
	    strcmp(ver->package_version, "1.22") != 0) {
		fprintf(stderr, "FAIL: package_version mismatch: %s\n",
			ver->package_version ? ver->package_version : "(null)");
		return 2;
	}
	if (!(ver->features & TSLIB_VERSION_VERSION)) {
		fprintf(stderr, "FAIL: TSLIB_VERSION_VERSION feature bit not set\n");
		return 3;
	}
	if (tslib_version() == NULL ||
	    strncmp(tslib_version(), "tslib 1.22", 10) != 0) {
		fprintf(stderr, "FAIL: tslib_version() prefix mismatch: %s\n",
			tslib_version() ? tslib_version() : "(null)");
		return 4;
	}
	/* Error-path exercise: opening an absent device must fail cleanly. */
	if (ts_open("/dev/tslib-consumer-no-such-device", 0) != NULL) {
		fprintf(stderr,
			"FAIL: ts_open() on absent device unexpectedly succeeded\n");
		return 5;
	}
	printf("tslib consumer test OK: version API and error path verified\n");
	return 0;
}
