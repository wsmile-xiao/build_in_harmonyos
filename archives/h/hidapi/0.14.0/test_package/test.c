/* test_package — consumer test for hidapi
   Calls real hidapi API: hid_version_str, hid_init, hid_enumerate, hid_exit.
   hid_init() may fail on headless CI systems without USB subsystem — that's OK,
   the test still validates that the library loads and API symbols resolve. */
#include <stdio.h>
#include <hidapi/hidapi.h>

int main(void) {
    /* Verify library is loaded and linked by calling version API */
    printf("hidapi version: %s\n", hid_version_str());

    /* Try to initialize — may fail on headless systems without USB hardware */
    int res = hid_init();
    if (res != 0) {
        printf("hid_init() returned %d (expected on headless systems)\n", res);
        printf("hidapi test: OK (library loaded, API callable)\n");
        return 0;
    }

    /* Enumerate devices — expected to find none on headless */
    struct hid_device_info *devs = hid_enumerate(0x0, 0x0);
    if (devs) {
        printf("Found HID devices\n");
        hid_free_enumeration(devs);
    } else {
        printf("No HID devices found (expected on headless systems)\n");
    }

    hid_exit();
    printf("hidapi test: OK\n");
    return 0;
}
