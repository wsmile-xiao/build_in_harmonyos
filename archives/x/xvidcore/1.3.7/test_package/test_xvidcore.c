#include <stdio.h>
#include <xvid.h>

int main(void) {
    /* Initialize xvidcore */
    xvid_gbl_init_t init;
    init.version = XVID_VERSION;
    init.debug = 0;
    init.cpu_flags = 0;
    if (xvid_global(NULL, XVID_GBL_INIT, &init, NULL) < 0) {
        fprintf(stderr, "xvid_global init failed\n");
        return 1;
    }

    /* Get xvidcore info (version, build string) */
    xvid_gbl_info_t info;
    info.version = XVID_VERSION;
    if (xvid_global(NULL, XVID_GBL_INFO, &info, NULL) < 0) {
        fprintf(stderr, "xvid_global info failed\n");
        return 1;
    }

    printf("xvidcore initialized successfully\n");
    printf("build: %s\n", info.build ? info.build : "(null)");
    printf("actual_version: %d\n", info.actual_version);
    printf("num_threads: %d\n", info.num_threads);
    return 0;
}
