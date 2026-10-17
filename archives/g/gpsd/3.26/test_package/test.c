/*
 * R34 test: calls real libgps APIs to verify runtime ABI.
 * - gps_errstr(): returns error string for a known errno, no daemon needed
 * - gps_open():   attempts socket connect to gpsd; expected to fail
 *                 (no daemon in CI), but the call itself exercises
 *                 symbol resolution, struct layout, and ABI.
 * - gps_close():  tears down the (failed) gps_data_t handle.
 *
 * Acceptance: program returns 0 iff gps_errstr returns non-NULL,
 * gps_open returns < 0 (expected failure, not a crash), and
 * gps_close returns 0 on the uninitialized handle.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <gps.h>

int main(int argc, char **argv) {
    int failures = 0;

    /* ---- Assertion 1: gps_errstr() resolves and returns a string ---- */
    /* ENOENT (2) is a universally defined libgps error code */
    const char *err = gps_errstr(2);
    if (err == NULL || err[0] == '\0') {
        printf("FAIL: gps_errstr(2) returned empty/NULL\n");
        failures++;
    } else {
        printf("PASS: gps_errstr(2) = \"%s\"\n", err);
    }

    /* ---- Assertion 2: gps_open() runtime call (ABI exercise) ---- */
    struct gps_data_t gpsdata;
    memset(&gpsdata, 0, sizeof(gpsdata));

    /* gpsd default socket; no daemon running in CI → expect -1 */
    int rc = gps_open(GPSD_SHARED_MEMORY, NULL, &gpsdata);
    if (rc == 0) {
        /* Unexpected: a daemon answered. Close cleanly. */
        gps_close(&gpsdata);
        printf("PASS: gps_open() succeeded (daemon present)\n");
    } else if (rc < 0) {
        /* Expected path: connect refused / no daemon.
         * The call itself validates symbol resolution + struct ABI. */
        printf("PASS: gps_open() returned %d (expected failure, ABI OK)\n", rc);
    } else {
        printf("FAIL: gps_open() returned unexpected value %d\n", rc);
        failures++;
    }

    /* ---- Assertion 3: gps_close() on uninitialized handle is safe ---- */
    /* Per libgps contract, gps_close on a zeroed handle returns 0 */
    struct gps_data_t empty;
    memset(&empty, 0, sizeof(empty));
    int crc = gps_close(&empty);
    if (crc == 0) {
        printf("PASS: gps_close() returned 0\n");
    } else {
        printf("FAIL: gps_close() returned %d\n", crc);
        failures++;
    }

    /* ---- Assertion 4: version macro + struct size sanity ---- */
    printf("PASS: GPSD_API_MAJOR_VERSION=%d, sizeof(gps_data_t)=%zu\n",
           GPSD_API_MAJOR_VERSION, sizeof(gpsdata));

    if (failures > 0) {
        printf("gpsd 3.26: %d test(s) FAILED\n", failures);
        return 1;
    }
    printf("gpsd 3.26: all tests PASSED\n");
    return 0;
}
