#include <stdio.h>
#include <string.h>
#include <mtdev.h>

int main(void) {
    /* Verify struct mtdev is accessible from the library header */
    struct mtdev dev;
    memset(&dev, 0, sizeof(dev));

    /* Verify struct layout: state pointer should be NULL after memset */
    if (dev.state != NULL) {
        fprintf(stderr, "dev.state should be NULL after memset\n");
        return 1;
    }

    /* Verify caps are zeroed */
    if (dev.caps.has_mtdata != 0) {
        fprintf(stderr, "caps.has_mtdata should be 0 after memset\n");
        return 1;
    }

    /* Verify mtdev_close is safe on zeroed struct (free(NULL) is no-op) */
    mtdev_close(&dev);

    /* Verify mtdev_new_open with invalid fd returns NULL (API linking check) */
    struct mtdev *new_dev = mtdev_new_open(-1);
    if (new_dev != NULL) {
        mtdev_close_delete(new_dev);
        fprintf(stderr, "mtdev_new_open(-1) should return NULL\n");
        return 1;
    }

    printf("test mtdev 1.1.7: OK\n");
    return 0;
}
