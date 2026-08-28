/* test_libusbmuxd.c — L1 test for libusbmuxd C API.
 *
 * Verifies the library links and its core API symbols resolve by calling
 * usbmuxd_get_device_list() (returns empty list / error on hosts without
 * a usbmuxd daemon or iOS device — acceptable, the point is link + ABI
 * correctness).
 */
#include <usbmuxd.h>
#include <stdio.h>

int main(void) {
    usbmuxd_device_info_t *dev_list = NULL;

    /* Probe the API: no usbmuxd daemon/device on OHOS returns a negative
     * error or empty list; both prove the library is linked & callable. */
    int ret = usbmuxd_get_device_list(&dev_list);
    if (ret < 0) {
        printf("usbmuxd_get_device_list: no daemon/device (ret=%d) — link OK\n", ret);
    } else {
        printf("usbmuxd_get_device_list: %d device(s) — link OK\n", ret);
        usbmuxd_device_list_free(&dev_list);
    }

    printf("test_libusbmuxd: ALL PASS\n");
    return 0;
}
