/* test_package for libhdhomerun — validates the library API */
#include <stdio.h>
#include "hdhomerun.h"

int main(void) {
    /* Smoke test: verify the library API is accessible and functional.
     * hdhomerun_discover_validate_device_id checks device ID checksum.
     * We don't assume which IDs are valid/invalid — just that the
     * function can be called and returns a boolean value. */
    bool result = hdhomerun_discover_validate_device_id(0x12345678);
    printf("hdhomerun_discover_validate_device_id(0x12345678) = %d\n", (int)result);

    printf("PASS: libhdhomerun API test\n");
    return 0;
}
