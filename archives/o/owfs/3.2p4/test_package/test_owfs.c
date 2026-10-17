/*
 * test_owfs.c — smoke test for owfs C API (libowcapi).
 *
 * Verifies that:
 *   1. OW_init() succeeds with the offline "fake" 1-wire bus master
 *      (simulates a DS18B20 temperature sensor; no hardware needed).
 *   2. OW_get("/") returns a non-empty device-tree listing.
 *   3. OW_finish() cleans up without crashing.
 *
 * Every check exits non-zero on failure so CI (L1) sees real results.
 */
#include <stdio.h>
#include <stdlib.h>

/* owfs C API header — installed as owcapi.h */
#include <owcapi.h>

int main(void)
{
    /* 1. Initialize with the fake adapter + a simulated DS18B20 sensor.
     *    OW_init returns 0 on success, a negative errno on failure. */
    ssize_t rc = OW_init("--fake=DS18B20");
    if (rc != 0) {
        fprintf(stderr, "FAIL: OW_init(\"--fake=DS18B20\") returned %zd\n", rc);
        return 1;
    }
    printf("PASS: OW_init with fake adapter\n");

    /* 2. Read the root directory — must list the simulated device tree.
     *    OW_get allocates *buffer (caller frees) and returns its length
     *    (> 0) or a negative errno. */
    char *buf = NULL;
    size_t buflen = 0;
    ssize_t len = OW_get("/", &buf, &buflen);
    if (len <= 0 || buf == NULL || buf[0] == '\0') {
        fprintf(stderr, "FAIL: OW_get(\"/\") returned %zd, buffer %s\n",
                len, buf ? "empty" : "NULL");
        if (buf) {
            free(buf);
        }
        OW_finish();
        return 1;
    }
    printf("PASS: OW_get(\"/\") returned %zd bytes of device tree\n", len);
    free(buf);

    /* 3. Clean up. */
    OW_finish();
    printf("PASS: OW_finish\n");

    printf("owfs consumer smoke passed\n");
    return 0;
}
