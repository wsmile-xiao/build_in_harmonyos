/* test.c — lightmapper 2.8 consumer test (R34).
 *
 * Actually calls the library's CPU-side public API on real buffers and
 * asserts the results:
 *   1. lmImageMin / lmImageMax return the true extremes of a known buffer.
 *   2. lmImagePower applies an in-place powf (gamma) and hits known values.
 *   3. lmImageDilate widens a non-zero area by one pixel.
 *   4. lmImageFtoUB converts a float image to 8-bit with the expected scaling.
 *   5. lmImageSaveTGAub writes a valid TGA file and returns LM_TRUE.
 *   6. lmImageAdd / lmImageScale apply in-place arithmetic.
 *
 * GL paths (lmCreate/lmBegin/lmEnd...) need a live OpenGL context and are not
 * exercised headless; the GL symbols are satisfied by gl_shim.c stubs that are
 * never executed here.
 */
#include <stdio.h>
#include <math.h>
#include <string.h>
#include <stdlib.h>

#define LIGHTMAPPER_IMPLEMENTATION
#include "gl_shim.h"
#include "lightmapper.h"

static int checks = 0;
static int failed = 0;

static void check(int ok, const char *what) {
    checks++;
    if (!ok) { failed++; printf("FAIL: %s\n", what); }
}

int main(void) {
    /* 3x2 RGB float image: 18 values, known min=0.1f, max=0.9f. */
    const int w = 3, h = 2, c = 3;
    float img[18];
    int i;
    for (i = 0; i < 18; i++) img[i] = 0.1f + 0.8f * (float)i / 17.0f;
    img[0] = 0.1f;      /* known min */
    img[17] = 0.9f;     /* known max */

    /* 1. min/max */
    {
        float mn = lmImageMin(img, w, h, c, LM_ALL_CHANNELS);
        float mx = lmImageMax(img, w, h, c, LM_ALL_CHANNELS);
        check(fabsf(mn - 0.1f) < 1e-6f, "lmImageMin == 0.1");
        check(fabsf(mx - 0.9f) < 1e-6f, "lmImageMax == 0.9");
        printf("min=%.4f max=%.4f\n", (double)mn, (double)mx);
    }

    /* 2. power (gamma): 0.5^2 = 0.25, 0.9^2 = 0.81 */
    {
        float tmp[18];
        memcpy(tmp, img, sizeof(tmp));
        lmImagePower(tmp, w, h, c, 2.0f, LM_ALL_CHANNELS);
        check(fabsf(tmp[0] - 0.01f) < 1e-5f, "lmImagePower 0.1^2 == 0.01");
        check(fabsf(tmp[17] - 0.81f) < 1e-5f, "lmImagePower 0.9^2 == 0.81");
        /* exponent 1.0 is identity */
        memcpy(tmp, img, sizeof(tmp));
        lmImagePower(tmp, w, h, c, 1.0f, LM_ALL_CHANNELS);
        check(fabsf(tmp[0] - 0.1f) < 1e-6f && fabsf(tmp[17] - 0.9f) < 1e-6f,
              "lmImagePower exponent 1.0 is identity");
    }

    /* 3. dilate: 2x2 single-channel, single non-zero pixel (bottom-right).
     * 4-neighbourhood (dx/dy = left/right/up/down): the bottom-right value
     * propagates to its left (idx1) and up (idx2) neighbours; the diagonal
     * (idx0) stays 0. */
    {
        const int dw = 2, dh = 2;
        const float src[4] = { 0.0f, 0.0f, 0.0f, 1.0f };
        float out[4] = { 0, 0, 0, 0 };
        lmImageDilate(src, out, dw, dh, 1);
        check(fabsf(out[3] - 1.0f) < 1e-6f, "lmImageDilate keeps source pixel");
        check(out[1] > 0.0f && out[2] > 0.0f,
              "lmImageDilate widened into 4-neighbours");
        check(out[0] == 0.0f,
              "lmImageDilate does not fill diagonal");
    }

    /* 4. FtoUB: max=1.0 -> 0.5 maps to 127 (round) */
    {
        const float src[2] = { 0.0f, 1.0f };
        unsigned char ub[2] = { 0, 0 };
        lmImageFtoUB(src, ub, 2, 1, 1, 1.0f);
        check(ub[0] == 0 && ub[1] == 255, "lmImageFtoUB 0.0->0, 1.0->255");
    }

    /* 5. TGA save */
    {
        unsigned char tga[6 * 3];
        for (i = 0; i < 6 * 3; i++) tga[i] = (unsigned char)(i % 256);
        const char *path = "lightmapper_test.tga";
        lm_bool ok = lmImageSaveTGAub(path, tga, w, h, c);
        check(ok == LM_TRUE, "lmImageSaveTGAub returns LM_TRUE");
        if (ok == LM_TRUE) {
            FILE *f = fopen(path, "rb");
            check(f != NULL, "lmImageSaveTGAub wrote a file");
            if (f) {
                unsigned char hdr[18];
                size_t n = fread(hdr, 1, 18, f);
                check(n == 18 && hdr[2] == 2 && hdr[12] == (w & 0xff) && hdr[14] == (h & 0xff),
                      "TGA header: type 2, width/height match");
                fclose(f);
            }
            remove(path);
        }
    }

    /* 6. add / scale */
    {
        float tmp[18];
        memcpy(tmp, img, sizeof(tmp));
        lmImageAdd(tmp, w, h, c, 1.0f, LM_ALL_CHANNELS);
        check(fabsf(tmp[0] - (0.1f + 1.0f)) < 1e-6f, "lmImageAdd +1.0");
        lmImageScale(tmp, w, h, c, 0.5f, LM_ALL_CHANNELS);
        check(fabsf(tmp[0] - 0.55f) < 1e-6f, "lmImageScale *0.5 after add");
    }

    if (failed) {
        printf("lightmapper test: %d/%d checks FAILED\n", failed, checks);
        return 1;
    }
    printf("lightmapper test: all %d checks passed\n", checks);
    return 0;
}