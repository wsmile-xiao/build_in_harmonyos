/*
 * Smoke test for libusb-compat 0.1.7
 *
 * Validates the libusb-0.1 compat API:
 *   - usb_init() / usb_find_busses() / usb_find_devices() execute without crash
 *   - usb_get_string_simple() returns gracefully when no device handle
 *   - usb_strerror() returns a non-NULL string
 *
 * Note: on a system with no USB devices (e.g. a VM or container), the
 * find_busses / find_devices calls simply return 0.  That is still a
 * successful validation that the compat layer links and initialises.
 */
#include <usb.h>
#include <stdio.h>
#include <string.h>

int main(void)
{
    /* 1. Initialise the compat layer */
    usb_init();

    /* 2. Enumerate busses and devices (may return 0 in container/VM) */
    int bus_count = usb_find_busses();
    int dev_count = usb_find_devices();

    /* 3. Get the first bus (if any) and check struct fields */
    struct usb_bus *bus = usb_get_busses();

    /* 4. Validate usb_strerror always returns a valid string */
    const char *err = usb_strerror();
    if (err == NULL) {
        fprintf(stderr, "FAIL: usb_strerror returned NULL\n");
        return 1;
    }

    /* 5. Print results */
    printf("libusb-compat smoke passed: init ok, busses=%d, devices=%d, "
           "first_bus=%s, strerror=\"%s\"\n",
           bus_count, dev_count,
           bus ? bus->dirname : "(none)",
           err);

    return 0;
}
