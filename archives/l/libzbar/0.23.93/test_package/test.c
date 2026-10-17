#include <stdio.h>
#include <stdlib.h>
#include <zbar.h>

int main(void) {
    /* Create and destroy an image scanner to verify libzbar API */
    zbar_image_scanner_t *scanner = zbar_image_scanner_create();
    if (!scanner) {
        fprintf(stderr, "FAIL: zbar_image_scanner_create returned NULL\n");
        return 1;
    }
    zbar_image_scanner_set_config(scanner, 0, ZBAR_CFG_ENABLE, 1);
    zbar_image_scanner_destroy(scanner);
    printf("OK: libzbar API test passed (scanner create/config/destroy)\n");
    return 0;
}
