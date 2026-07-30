#include <babl/babl.h>
#include <stdio.h>

int main(void) {
    babl_init();

    /* Retrieve a well-known pixel format and check it exists */
    const Babl *rgba8 = babl_format("R'G'B'A u8");
    if (!rgba8) {
        fprintf(stderr, "FAIL: babl_format(\"R'G'B'A u8\") returned NULL\n");
        babl_exit();
        return 1;
    }

    /* Verify bytes-per-pixel is 4 (4 channels x 1 byte each) */
    int bpp = babl_format_get_bytes_per_pixel(rgba8);
    if (bpp != 4) {
        fprintf(stderr, "FAIL: bytes_per_pixel=%d (expected 4)\n", bpp);
        babl_exit();
        return 1;
    }

    printf("test babl 0.1.126: OK (R'G'B'A u8 = %d bytes/pixel)\n", bpp);
    babl_exit();
    return 0;
}
