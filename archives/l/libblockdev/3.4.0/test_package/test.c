#include <stdio.h>
#include <blockdev/blockdev.h>

int main(void) {
    /* Verify libblockdev core is linked: bd_is_initialized() returns FALSE before init */
    if (bd_is_initialized()) {
        fprintf(stderr, "ERROR: bd_is_initialized() should return FALSE before init\n");
        return 1;
    }

    /* Verify bd_init_error_quark() returns a valid GQuark */
    GQuark q = bd_init_error_quark();
    if (q == 0) {
        fprintf(stderr, "ERROR: bd_init_error_quark() returned 0\n");
        return 1;
    }

    printf("test libblockdev 3.4.0: OK\n");
    return 0;
}
