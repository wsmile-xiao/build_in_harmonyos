#include <stdio.h>
#include <sixel.h>

int main(void) {
    /* Test 1: Create a dither object */
    sixel_dither_t *dither = NULL;
    SIXELSTATUS status = sixel_dither_new(&dither, 256, NULL);
    if (!SIXEL_SUCCEEDED(status)) {
        fprintf(stderr, "FAIL: sixel_dither_new returned 0x%04x\n", status);
        return 1;
    }
    printf("OK: sixel_dither_new succeeded (256 colors)\n");

    /* Test 2: Create an encoder object */
    sixel_encoder_t *encoder = NULL;
    status = sixel_encoder_new(&encoder, NULL);
    if (!SIXEL_SUCCEEDED(status)) {
        fprintf(stderr, "FAIL: sixel_encoder_new returned 0x%04x\n", status);
        sixel_dither_destroy(dither);
        return 1;
    }
    printf("OK: sixel_encoder_new succeeded\n");

    /* Test 3: Verify library version */
    printf("OK: libsixel version = %s\n", LIBSIXEL_VERSION);

    /* Cleanup */
    sixel_encoder_unref(encoder);
    printf("OK: sixel_encoder_unref succeeded\n");
    sixel_dither_destroy(dither);
    printf("OK: sixel_dither_destroy succeeded\n");

    return 0;
}
