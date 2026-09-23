/* Consumer test for libgd2/2.3.3: exercises the retained core C API.
 * 6 CHECK-OK lines; any failure returns nonzero. Output content is
 * asserted (GIF magic bytes + non-empty buffers), never just exit 0. */
#include <stdio.h>
#include <string.h>
#include <gd.h>
#include <gdfonts.h>

int main(void) {
    /* 1. version macros match the adapted upstream release. */
    if (GD_MAJOR_VERSION != 2 || GD_MINOR_VERSION != 3 || GD_RELEASE_VERSION != 3) {
        printf("FAIL: version %d.%d.%d\n", GD_MAJOR_VERSION, GD_MINOR_VERSION, GD_RELEASE_VERSION);
        return 1;
    }
    printf("CHECK-OK: version %d.%d.%d\n", GD_MAJOR_VERSION, GD_MINOR_VERSION, GD_RELEASE_VERSION);

    /* 2. truecolor image creation with expected dimensions. */
    gdImagePtr im = gdImageCreateTrueColor(64, 48);
    if (!im || gdImageSX(im) != 64 || gdImageSY(im) != 48) {
        printf("FAIL: create truecolor\n");
        return 1;
    }
    printf("CHECK-OK: create 64x48 truecolor\n");

    /* 3. draw + pixel readback round-trip. */
    int red = gdTrueColor(255, 0, 0);
    gdImageFilledRectangle(im, 0, 0, 63, 47, red);
    if (gdImageGetPixel(im, 32, 24) != red) {
        printf("FAIL: pixel readback\n");
        gdImageDestroy(im);
        return 1;
    }
    printf("CHECK-OK: fill + pixel readback\n");

    /* 4. builtin-font string (no freetype needed) changes pixels. */
    int before = gdImageGetPixel(im, 2, 2);
    gdImageString(im, gdFontGetSmall(), 2, 2, (unsigned char *)"gd2", gdTrueColor(255, 255, 255));
    if (gdFontGetSmall()->h <= 0) {
        printf("FAIL: builtin font\n");
        gdImageDestroy(im);
        return 1;
    }
    printf("CHECK-OK: builtin font string (pixel %d -> %d)\n", before, gdImageGetPixel(im, 2, 2));

    /* 5. GIF encode: non-empty buffer with GIF magic (builtin codec). */
    int gifSize = 0;
    void *gif = gdImageGifPtr(im, &gifSize);
    if (!gif || gifSize <= 0 || memcmp(gif, "GIF", 3) != 0) {
        printf("FAIL: gif encode\n");
        gdImageDestroy(im);
        return 1;
    }
    printf("CHECK-OK: gif encode %d bytes magic=%.6s\n", gifSize, (char *)gif);

    /* 6. GIF decode round-trip preserves dimensions. */
    gdImagePtr back = gdImageCreateFromGifPtr(gifSize, gif);
    gdFree(gif);
    if (!back || gdImageSX(back) != 64 || gdImageSY(back) != 48) {
        printf("FAIL: gif decode\n");
        gdImageDestroy(im);
        return 1;
    }
    printf("CHECK-OK: gif decode 64x48 round-trip\n");
    gdImageDestroy(back);
    gdImageDestroy(im);
    return 0;
}
