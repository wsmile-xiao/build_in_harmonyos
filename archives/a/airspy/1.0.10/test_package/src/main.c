#include <stdio.h>
#include <string.h>
#include "airspy.h"

/* Smoke test: exercise libairspy without a connected device.
   airspy_init() loads the libusb backend; airspy_exit() releases it.
   airspy_lib_version() reads the compile-time version baked into the
   installed header and shared library. */
int main(void)
{
    airspy_lib_version_t ver;
    airspy_lib_version(&ver);

    const char expect[] = "1.0.10";
    if (ver.major_version != 1 || ver.minor_version != 0 || ver.revision != 10) {
        fprintf(stderr, "FAIL: lib version %d.%d.%d != 1.0.10\n",
                ver.major_version, ver.minor_version, ver.revision);
        return 1;
    }

    int rc = airspy_init();
    if (rc != AIRSPY_SUCCESS) {
        fprintf(stderr, "FAIL: airspy_init() returned %d\n", rc);
        return 2;
    }

    /* airspy_list_devices() with serials=NULL, count=0 is a valid probe
       that returns 0 when no AirSpy hardware is attached. */
    int n = airspy_list_devices(NULL, 0);
    (void)n;

    airspy_exit();
    printf("airspy version %s (%d.%d.%d) ok\n", AIRSPY_VERSION,
           ver.major_version, ver.minor_version, ver.revision);
    return 0;
}
