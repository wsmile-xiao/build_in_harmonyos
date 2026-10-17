/*
 * test_duo.c — Consumer test for libduo (duo-unix 1.11.3)
 *
 * Verifies that the libduo library can be linked against and that its
 * public API (duo_open / duo_geterr / duo_close) is callable.
 *
 * duo_open() with a NULL cafile uses the built-in CA certificate bundle
 * (cacert.h), so no external files or network access are required.
 */
#include <stdio.h>
#include <stdlib.h>

#include "duo.h"

int main(void) {
    duo_t *d;

    /* duo_open sets up an API handle; NULL cafile → built-in CA bundle.
     * No network connection is made at this stage. */
    d = duo_open("api-test.duosecurity.com", "DI-test-ikey", "deadbeef-test-skey",
                 "test_duo", NULL, 5, NULL);

    if (d == NULL) {
        /* duo_open can fail if OpenSSL initialization fails; report and exit
         * non-zero so the test is meaningful (a real link/runtime failure). */
        fprintf(stderr, "test_duo: duo_open returned NULL\n");
        return 1;
    }

    /* duo_geterr should return NULL (no error yet) on a freshly-opened handle */
    const char *err = duo_geterr(d);
    if (err != NULL) {
        fprintf(stderr, "test_duo: unexpected error on fresh handle: %s\n", err);
        duo_close(d);
        return 1;
    }

    /* Clean up */
    duo_close(d);

    printf("test_duo: libduo API smoke test PASSED\n");
    return 0;
}
