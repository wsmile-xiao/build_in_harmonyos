/* test_libimobiledevice.c — L1 test for libimobiledevice C API.
 *
 * Verifies the library links and its core API symbols resolve by calling
 * idevice_get_device_list() (returns error on hosts without a usbmuxd
 * daemon / iOS device — acceptable, the point is link + ABI correctness).
 */
#include <libimobiledevice/libimobiledevice.h>
#include <stdio.h>

int main(void) {
    char **devices = NULL;
    int count = 0;

    /* Probe the API: no usbmuxd daemon/device on OHOS returns a negative
     * error or empty list; both prove the library is linked & callable. */
    idevice_error_t ret = idevice_get_device_list(&devices, &count);
    if (ret == IDEVICE_E_SUCCESS) {
        printf("idevice_get_device_list: %d device(s) — link OK\n", count);
        idevice_device_list_free(devices);
    } else {
        printf("idevice_get_device_list: no daemon/device (ret=%d) — link OK\n", (int)ret);
    }

    printf("test_libimobiledevice: ALL PASS\n");
    return 0;
}
