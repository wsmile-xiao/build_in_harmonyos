#include <leptonica/allheaders.h>

#include <stdio.h>

int main(void) {
    PIX *original = NULL;
    PIX *decoded = NULL;
    l_uint8 *png = NULL;
    size_t png_size = 0;
    l_int32 same = 0;
    l_uint32 pixel = 0;
    int result = 1;

    original = pixCreate(2, 2, 32);
    if (!original || pixSetPixel(original, 0, 0, 0xff000000U))
        goto done;
    if (pixWriteMemPng(&png, &png_size, original, 0.0f) || !png || !png_size)
        goto done;
    decoded = pixReadMemPng(png, png_size);
    if (!decoded || pixEqual(original, decoded, &same) || !same)
        goto done;
    if (pixGetPixel(decoded, 0, 0, &pixel) || pixel != 0xff000000U)
        goto done;
    puts("leptonlib PNG memory roundtrip consumer: PASS");
    result = 0;
done:
    pixDestroy(&original);
    pixDestroy(&decoded);
    lept_free(png);
    return result;
}
