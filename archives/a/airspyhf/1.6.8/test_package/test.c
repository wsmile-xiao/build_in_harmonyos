#include <stdio.h>
#include <string.h>
#include <stdint.h>

#include <airspyhf.h>

/* Real API test: calls airspyhf_lib_version() (guaranteed to work) and
 * airspyhf_list_devices() (exercises the libusb/1.0.27 dependency chain).
 * On this sandbox no USB subsystem is exposed, so libusb_init() returns -1
 * and list_devices() reports that failure — the version assertion remains
 * the hard gate proving the library links and loads. */
int main(void)
{
	airspyhf_lib_version_t ver = {0};
	int rc;

	/* airspyhf_lib_version() is void; zero-init so fields are defined before use */
	airspyhf_lib_version(&ver);
	printf("AirSpy HF library version: %u.%u.%u\n",
	       ver.major_version, ver.minor_version, ver.revision);

	if (ver.major_version != 1 || ver.minor_version != 6 || ver.revision != 8) {
		fprintf(stderr, "FAIL: unexpected library version\n");
		return 1;
	}
	printf("airspyhf_lib_version() ok\n");

	/* Probe for attached devices. libusb_init() fails on sandboxes without
	 * USB access (rc == -1); the call must still run and be reported. */
	rc = airspyhf_list_devices(NULL, 0);
	printf("airspyhf_list_devices() rc=%d %s\n", rc,
	       rc < 0 ? "(no USB access in sandbox — platform limitation)" :
	       "(no AirSpy HF+ attached)");
	if (rc < 0) {
		printf("note: libusb not usable here; version API already validated\n");
	}

	printf("test airspyhf 1.6.8: OK\n");
	return 0;
}
