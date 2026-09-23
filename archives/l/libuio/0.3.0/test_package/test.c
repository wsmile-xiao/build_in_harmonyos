/*
 * test_package for libuio 0.3.0 — exercises the public enumeration/lookup
 * API (R34).
 *
 * libuio reads /sys/class/uio and /dev/uio*. On a system without UIO
 * devices (typical HarmonyOS PC) uio_find_devices() legitimately returns
 * NULL, so the test then verifies the lookup helpers' negative paths; on a
 * system with UIO devices it prints each device's sysfs attributes.
 */
#include <stdio.h>
#include <stdlib.h>

#include <libuio.h>

int main(void)
{
	struct uio_info_t **list;
	struct uio_info_t *probe;
	int i, found = 0;

	/* 1) enumerate UIO devices via /sys/class/uio */
	list = uio_find_devices ();
	if (list != NULL) {
		for (i = 0; list[i] != NULL; i++) {
			struct uio_info_t *info = list[i];
			char *name = uio_get_name (info);
			char *version = uio_get_version (info);
			char *devname = uio_get_devname (info);

			printf ("uio%d: name=%s version=%s dev=%s major=%d minor=%d maps=%d\n",
				uio_get_minor (info),
				name ? name : "?",
				version ? version : "?",
				devname ? devname : "?",
				uio_get_major (info),
				uio_get_minor (info),
				uio_get_maxmap (info));
			found++;
		}
		free (list);
	}
	printf ("uio_find_devices: %d device(s)\n", found);

	/* 2) negative lookups must return NULL */
	probe = uio_find_by_uio_name ((char *) "no-such-uio-device");
	if (probe != NULL) {
		fprintf (stderr, "FAIL: bogus uio name unexpectedly resolved\n");
		return 1;
	}
	printf ("uio_find_by_uio_name: NULL as expected\n");

	probe = uio_find_by_uio_num (999999);
	if (probe != NULL) {
		fprintf (stderr, "FAIL: bogus uio number unexpectedly resolved\n");
		return 1;
	}
	printf ("uio_find_by_uio_num: NULL as expected\n");

	printf ("libuio test OK\n");
	return 0;
}
