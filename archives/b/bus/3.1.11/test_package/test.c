/* test.c — consumer smoke test for bus 3.1.11 (libbus).
 *
 * Uses only the installed public header bus.h and links -lbus, exactly like a
 * third-party upper-layer component would. Calls a real public API (bus_open):
 * opening a non-existent bus file returns -1 with errno=ENOENT without
 * reaching the semget/shmget syscalls (which the OHOS sandbox blocks with
 * SIGSYS), so this path is runnable while still exercising genuine library
 * code (fopen/getline/error handling inside libbus).
 */
#include <bus.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>

int main(void)
{
	bus_t bus;
	int r;

	errno = 0;
	r = bus_open(&bus, "/nonexistent/ohc-bus-test", BUS_RDONLY);
	if (r != -1) {
		fprintf(stderr, "FAIL: bus_open returned %d, expected -1\n", r);
		return 1;
	}
	if (errno != ENOENT) {
		fprintf(stderr, "FAIL: bus_open errno=%d (%s), expected ENOENT\n",
			errno, strerror(errno));
		return 1;
	}
	printf("PASS: bus_open(nonexistent) -> -1 errno=ENOENT (%s)\n", strerror(errno));
	return 0;
}
