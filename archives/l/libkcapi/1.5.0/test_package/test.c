/* Consumer smoke test for libkcapi on OHOS.
 *
 * Exercises only the pure user-space parts of the API that do not require
 * kernel AF_ALG sockets (which are not exposed to unprivileged apps on OHOS):
 *   - kcapi_versionstring() / kcapi_version()   library identity
 */
#include <stdio.h>
#include <kcapi.h>

int main(void)
{
	char versionbuf[100];
	uint32_t version;

	kcapi_versionstring(versionbuf, sizeof(versionbuf));
	version = kcapi_version();
	printf("libkcapi version: %s (0x%08x)\n", versionbuf, version);

	if (version == 0) {
		fprintf(stderr, "FAIL: kcapi_version() returned 0\n");
		return 1;
	}

	printf("PASS\n");
	return 0;
}
