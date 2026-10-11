/* test_libimobiledevice.c - consumer test for libimobiledevice 1.4.0.
 *
 * Verifies the library links and its core API symbols resolve by calling
 * the public API: idevice_get_device_list() returns an error/empty list on
 * hosts without a usbmuxd daemon / iOS device (OHOS has neither), which
 * still proves link + ABI correctness; idevice_new() with a bogus UDID
 * must fail cleanly (error path); idevice_set_debug_level() is a no-op
 * setter that always succeeds.
 */
#include <libimobiledevice/libimobiledevice.h>
#include <stdio.h>

static int g_checks = 0;

#define CHECK(cond, msg) \
    do { \
        if (!(cond)) { \
            printf("FAIL: %s\n", msg); \
            return 1; \
        } \
        g_checks++; \
    } while (0)

int main(void)
{
    char **devices = NULL;
    int count = 0;

    /* Probe 1: device list API is linked & callable (no daemon on OHOS
     * returns a negative error or an empty list - both fine). */
    idevice_error_t ret = idevice_get_device_list(&devices, &count);
    if (ret == IDEVICE_E_SUCCESS) {
        printf("idevice_get_device_list: %d device(s) - link OK\n", count);
        idevice_device_list_free(devices);
    } else {
        printf("idevice_get_device_list: no daemon/device (ret=%d) - link OK\n",
               (int)ret);
    }
    CHECK(1, "idevice_get_device_list + idevice_device_list_free callable");

    /* Probe 2: creating a device with a bogus UDID must fail cleanly. */
    idevice_t dev = NULL;
    ret = idevice_new(&dev, "0000000000000000000000000000000000000000");
    CHECK(ret != IDEVICE_E_SUCCESS && dev == NULL,
          "idevice_new with bogus UDID fails cleanly");

    /* Probe 3: debug level setter (always-succeeds API). */
    idevice_set_debug_level(0);
    CHECK(1, "idevice_set_debug_level callable");

    printf("test_libimobiledevice: %d checks ALL PASS\n", g_checks);
    return 0;
}
