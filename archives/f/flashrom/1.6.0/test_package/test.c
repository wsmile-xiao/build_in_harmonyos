/* test_package/test.c — flashrom L1 consumer test (R34: uses libflashrom API) */
#include <libflashrom.h>
#include <stdio.h>

int main(void) {
    /* Initialize libflashrom without self-check (safe, no hardware access) */
    int ret = flashrom_init(0);
    if (ret != 0) {
        fprintf(stderr, "flashrom_init failed: %d\n", ret);
        return 1;
    }

    /* Set log level to INFO */
    flashrom_set_log_level(FLASHROM_MSG_INFO);

    /* Shut down cleanly */
    ret = flashrom_shutdown();
    if (ret != 0) {
        fprintf(stderr, "flashrom_shutdown failed: %d\n", ret);
        return 1;
    }

    printf("flashrom_init + flashrom_shutdown: OK\n");
    return 0;
}
