/*
 * test_package for jeolib-miallib 1.1.7 — real API usage test.
 * Creates an 8x8 t_UCHAR image, runs histo1d() and erode4()/dilate4(),
 * and verifies results.
 */
#include <stdio.h>
#include <string.h>
#include "miallib.h"

int main(void)
{
    IMAGE *im, *h;
    UCHAR *pix;
    size_t i, n = 8 * 8;
    int failures = 0;

    im = create_image(t_UCHAR, 8, 8, 1);
    if (im == NULL) {
        printf("FAIL: create_image returned NULL\n");
        return 1;
    }
    pix = (UCHAR *)im->p_im;
    for (i = 0; i < n; i++)
        pix[i] = (UCHAR)(i % 7);

    /* 1-D histogram: for t_UCHAR input the result has (max+1) bins of INT32 */
    h = histo1d(im);
    if (h == NULL) {
        printf("FAIL: histo1d returned NULL\n");
        failures++;
    } else {
        INT32 *hb;
        long int sum = 0;
        long int nbins = (long int)GetImNx(h);
        int j;
        if (GetImDataType(h) != t_HST1D) {
            printf("FAIL: histogram type %d != t_HST1D\n", (int)GetImDataType(h));
            failures++;
        }
        hb = (INT32 *)h->p_im;
        for (j = 0; j < nbins; j++)
            sum += hb[j];
        if (sum != (long int)n) {
            printf("FAIL: histogram sum %ld != %d\n", sum, (int)n);
            failures++;
        }
        free_image(h);
    }

    /* morphological erosion + dilation by unit structuring element */
    if (erode4(im, 1, 1) != 0) {
        printf("FAIL: erode4 returned error\n");
        failures++;
    }
    if (dilate4(im, 1, 1) != 0) {
        printf("FAIL: dilate4 returned error\n");
        failures++;
    }

    free_image(im);

    if (failures == 0) {
        printf("PASS: miallib create_image/histo1d/erode4/dilate4 all OK\n");
        return 0;
    }
    return 1;
}
