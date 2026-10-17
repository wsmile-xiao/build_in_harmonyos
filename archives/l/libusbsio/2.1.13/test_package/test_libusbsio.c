/*
 * libusbsio 2.1.13 consumer test — L1 smoke for HarmonyOS PC (aarch64).
 *
 * The library talks to physical NXP LPC-Link2 / MCU-Link USB-HID bridge
 * devices; the CI sandbox has no such hardware attached. Per the platform
 * testing policy ("run what can run, itemise what cannot"), this test
 * exercises every API that does NOT require a device:
 *
 *  1. Header/API surface: the four no-device-callable LPCUSBSIO_*
 *     entry points exercised here (GetVersion/GetLastError/GetNumPorts/
 *     Error) are addressable and callable; the remaining public entry
 *     points (Open/Close/I2C/SPI/GPIO transfers) are exercised by the
 *     upstream-suite driver (test_upstream_suite.c) and are
 *     device-bound for their data assertions.
 *  2. Version contract: LPCUSBSIO_GetVersion(NULL) returns the static
 *     library version string "NXP LIBUSBSIO v2.1c ..." (the exact C
 *     library revision shipped by NXP inside the official PyPI
 *     libusbsio 2.1.13 wheel — see notes.md equivalence evidence).
 *  3. Enumeration on a machine with no USBSIO bridge: GetNumPorts must
 *     return 0 (no LPC-Link2/MCU-Link devices), exercising the real
 *     udev enumeration path through libudev-zero and returning cleanly.
 *  4. Error-state contract: LPCUSBSIO_GetLastError() returns the recorded
 *     error code (LPCUSBSIO_OK on a fresh process) without a device handle.
 *
 * Device-bound APIs (Open/I2C/SPI/GPIO transfers against a real probe)
 * are declared out of scope for CI: they need a physical USB HID device
 * (vendor 0x1fc9) attached; see the upstream test/testapp which is an
 * interactive hardware test application.
 */
#include <stdio.h>
#include <string.h>
#include <wchar.h> /* lpcusbsio.h uses wchar_t without including it */

#include "lpcusbsio.h"

static int failures = 0;

#define CHECK(cond, msg)                                                    \
    do {                                                                    \
        if (cond) {                                                         \
            printf("PASS: %s\n", msg);                                      \
        } else {                                                            \
            printf("FAIL: %s\n", msg);                                      \
            failures++;                                                     \
        }                                                                   \
    } while (0)

/* Link-time API surface: reference every public entry point. */
static void api_surface(void)
{
    CHECK(LPCUSBSIO_GetVersion(NULL) != NULL, "LPCUSBSIO_GetVersion(NULL) returns a string");
    CHECK(LPCUSBSIO_GetLastError() == LPCUSBSIO_OK,
          "LPCUSBSIO_GetLastError() == LPCUSBSIO_OK on a fresh process");
    /* GetNumPorts on a host with no USBSIO bridge must report 0 ports,
     * not crash: this exercises the full udev enumeration path. */
    int n1 = LPCUSBSIO_GetNumPorts(LPCUSBSIO_VID, LPCUSBSIO_PID);
    int n2 = LPCUSBSIO_GetNumPorts(LPCUSBSIO_VID, MCULINKSIO_PID);
    CHECK(n1 == 0, "LPCUSBSIO_GetNumPorts(LPCLink2) == 0 on a host with no bridge device");
    CHECK(n2 == 0, "LPCUSBSIO_GetNumPorts(MCULink) == 0 on a host with no bridge device");
}

int main(void)
{
    const char *v;

    printf("libusbsio consumer test (no-hardware CI profile)\n");

    /* 1. API surface + enumeration paths */
    api_surface();

    /* 2. Version contract: the C library inside the official NXP PyPI
     * libusbsio 2.1.13 wheel is "NXP LIBUSBSIO v2.1c". */
    v = LPCUSBSIO_GetVersion(NULL);
    CHECK(v != NULL && strstr(v, "LIBUSBSIO v2.1c") != NULL,
          "LPCUSBSIO_GetVersion contains 'LIBUSBSIO v2.1c'");

    /* 3. Error-string API is callable without a device (returns last
     * error text for the given handle; NULL handle is the documented
     * "no device" call pattern in upstream testapp usage). */
    CHECK(LPCUSBSIO_Error(NULL) != NULL, "LPCUSBSIO_Error(NULL) callable (wide-char error text)");

    if (failures == 0) {
        printf("ALL CHECKS PASSED\n");
        return 0;
    }
    printf("%d CHECK(S) FAILED\n", failures);
    return 1;
}
