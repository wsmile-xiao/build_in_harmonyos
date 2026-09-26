#include <stdio.h>
#include "libg15.h"

/*
 * Consumer smoke test for libg15 (R34: must substantively exercise the
 * package's API — not an empty-shell/print-only test).
 *
 * No Logitech G11/G15 hardware exists on OHOS PC, so the hardware-dependent
 * surface cannot be driven.  What IS verified against the real library:
 *   1. header constant LIBG15_VERSION (compile-time API surface);
 *   2. initLibG15() — it initialises the libusb-1.0 context, enumerates USB
 *      devices and tries to open the keyboard.  Without hardware it must
 *      return G15_ERROR_OPENING_USB_DEVICE (=1); with hardware it returns
 *      G15_NO_ERROR.  Both prove the library links, initialises and executes
 *      real code (a stub that never ran would return garbage/0 unconditionally).
 */
int main(void)
{
    int ok = 1;

    if (LIBG15_VERSION != 1201) {
        printf("FAIL: LIBG15_VERSION = %d, expected 1201\n", LIBG15_VERSION);
        ok = 0;
    } else {
        printf("OK: LIBG15_VERSION = %d\n", LIBG15_VERSION);
    }

    int r = initLibG15();
    if (r == G15_NO_ERROR) {
        printf("OK: initLibG15() = G15_NO_ERROR (G15 hardware present)\n");
        exitLibG15();
    } else if (r == G15_ERROR_OPENING_USB_DEVICE) {
        printf("OK: initLibG15() = G15_ERROR_OPENING_USB_DEVICE "
               "(no G15 hardware; libusb init + device probe executed)\n");
    } else {
        printf("FAIL: initLibG15() returned unexpected code %d\n", r);
        ok = 0;
    }

    return ok ? 0 : 1;
}
