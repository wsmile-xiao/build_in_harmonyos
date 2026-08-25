/*
 * test_zbar.c — Verify libzbar is functional.
 * Creates a zbar image scanner and checks it initializes correctly.
 */
#include <zbar.h>
#include <stdio.h>

int main(int argc, char *argv[])
{
    zbar_image_scanner_t *scanner = NULL;
    int rc = 1;
    unsigned major, minor, patch;

    /* Initialize zbar */
    zbar_set_verbosity(0);
    scanner = zbar_image_scanner_create();
    if (!scanner) {
        fprintf(stderr, "FAIL: zbar_image_scanner_create() returned NULL\n");
        goto cleanup;
    }

    /* Enable all barcode types */
    if (zbar_image_scanner_set_config(scanner, ZBAR_NONE,
                                      ZBAR_CFG_ENABLE, 1) != 0) {
        fprintf(stderr, "FAIL: zbar_image_scanner_set_config() failed\n");
        goto cleanup;
    }

    /* Print version */
    zbar_version(&major, &minor, &patch);
    printf("PASS: libzbar scanner created and configured\n");
    printf("zbar version: %u.%u.%u\n", major, minor, patch);
    rc = 0;

cleanup:
    if (scanner)
        zbar_image_scanner_destroy(scanner);
    return rc;
}
