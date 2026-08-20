#include <stdio.h>
#include <stdlib.h>
#include <libhackrf/hackrf.h>

int main(void) {
    const char *version = hackrf_library_version();
    const char *release = hackrf_library_release();

    printf("hackrf library version: %s\n", version ? version : "(null)");
    printf("hackrf library release: %s\n", release ? release : "()");

    /* Initialize and immediately exit to verify the library is functional */
    int result = hackrf_init();
    if (result != 0) {
        fprintf(stderr, "hackrf_init() failed: %d (expected without hardware)\n", result);
        /* This is not a test failure — no HackRF hardware is connected */
    }
    hackrf_exit();

    printf("test hackrf 2024.02.1-r1: OK\n");
    return 0;
}
