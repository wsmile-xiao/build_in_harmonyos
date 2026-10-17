/* Consumer test for libsir 2.2.6 (R34: must actually exercise the API).
 * Initializes libsir, logs a debug message through the library, and
 * verifies the version retrieval API before cleaning up. */
#include <stdio.h>
#include <string.h>
#include <sir.h>

int main(void) {
    sirinit si = {0};

    if (!sir_makeinit(&si)) {
        fprintf(stderr, "sir_makeinit failed\n");
        return 1;
    }
    if (!sir_init(&si)) {
        fprintf(stderr, "sir_init failed\n");
        return 1;
    }
    if (!sir_isinitialized()) {
        fprintf(stderr, "sir_isinitialized returned false\n");
        sir_cleanup();
        return 1;
    }

    const char* ver = sir_getversionstring();
    if (NULL == ver || 0 == strlen(ver)) {
        fprintf(stderr, "sir_getversionstring returned empty\n");
        sir_cleanup();
        return 1;
    }
    printf("libsir %s: logging via library API\n", ver);

    if (!sir_debug("consumer test message")) {
        fprintf(stderr, "sir_debug failed\n");
        sir_cleanup();
        return 1;
    }
    if (!sir_notice("consumer test notice")) {
        fprintf(stderr, "sir_notice failed\n");
        sir_cleanup();
        return 1;
    }

    if (!sir_cleanup()) {
        fprintf(stderr, "sir_cleanup failed\n");
        return 1;
    }
    printf("test libsir %s: OK\n", ver);
    return 0;
}
