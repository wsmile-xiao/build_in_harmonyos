/**
 * test_di_consumer — Minimal consumer of libdi
 *
 * Verifies that di.h is accessible and that the library can be linked.
 * Calls di_initialize() to exercise basic API paths.
 * This is a smoke test, not a full functional validation.
 */
#include <stdio.h>
#include <stdlib.h>

#include "di.h"

int main(void) {
    void *di_data;
    const char *ver;

    /* Initialize the library. */
    di_data = di_initialize();
    if (di_data == NULL) {
        fprintf(stderr, "di_initialize returned NULL\n");
        return 1;
    }

    /* Verify library version string is accessible */
    ver = di_version();
    fprintf(stdout, "di version: %s\n", ver != NULL ? ver : "(null)");

    /* Clean up */
    di_cleanup(di_data);

    fprintf(stdout, "libdi consumer test PASSED\n");
    return 0;
}
