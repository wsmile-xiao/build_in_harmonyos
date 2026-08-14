/*
 * test_imagemagick.c — Verify MagickWand library is functional.
 * Creates a 100x100 transparent image and checks its dimensions.
 */
#include <MagickWand/MagickWand.h>
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char *argv[])
{
    MagickWand *wand = NULL;
    int width = 100, height = 100;
    int rc = 1;

    MagickWandGenesis();
    wand = NewMagickWand();
    if (!wand) {
        fprintf(stderr, "FAIL: NewMagickWand() returned NULL\n");
        goto cleanup;
    }

    /* Create a transparent image */
    if (MagickSetSize(wand, width, height) == MagickFalse) {
        fprintf(stderr, "FAIL: MagickSetSize() failed\n");
        goto cleanup;
    }

    if (MagickReadImage(wand, "xc:none") == MagickFalse) {
        fprintf(stderr, "FAIL: MagickReadImage() failed\n");
        goto cleanup;
    }

    /* Verify dimensions */
    unsigned long actual_w = MagickGetImageWidth(wand);
    unsigned long actual_h = MagickGetImageHeight(wand);

    if (actual_w == (unsigned long)width && actual_h == (unsigned long)height) {
        printf("PASS: MagickWand created %lux%lu image\n", actual_w, actual_h);
        rc = 0;
    } else {
        fprintf(stderr, "FAIL: expected %dx%d but got %lux%lu\n",
                width, height, actual_w, actual_h);
        goto cleanup;
    }

cleanup:
    if (wand)
        DestroyMagickWand(wand);
    MagickWandTerminus();
    return rc;
}
