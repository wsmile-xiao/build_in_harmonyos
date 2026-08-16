#include <stdio.h>
#include <string.h>
#include <xvid.h>

int main(void) {
    xvid_gbl_init_t init;
    memset(&init, 0, sizeof(init));
    init.version = XVID_VERSION;

    int rc = xvid_global(NULL, XVID_GBL_INIT, &init, NULL);
    if (rc == 0) {
        printf("xvidcore init OK (version %d.%d.%d)\n",
               XVID_VERSION_MAJOR(XVID_VERSION),
               XVID_VERSION_MINOR(XVID_VERSION),
               XVID_VERSION_PATCH(XVID_VERSION));
        return 0;
    }
    printf("xvidcore init FAILED rc=%d\n", rc);
    return 1;
}