/*
 * test_lqr_package.c — consumer-view test for the packaged liblqr 0.4.3.
 *
 * Includes the installed <lqr.h> (via -I include/lqr-1), links the packaged
 * liblqr-1 + glib, and exercises the core seam-carving API with a small
 * deterministic image.  Compiled and run by test_package/conanfile.py test().
 *
 * Exit 0 on success, 1 on failure; prints PASS/FAIL per assertion.
 */
#include <stdio.h>
#include <string.h>
#include <lqr.h>

static int g_assertions = 0;
static int g_failures = 0;

static void check(int cond, const char *what)
{
    g_assertions++;
    if (cond)
    {
        printf("PASS: %s\n", what);
    }
    else
    {
        g_failures++;
        printf("FAIL: %s\n", what);
        fprintf(stderr, "FAIL: %s\n", what);
    }
}

int main(void)
{
    /* 8x4 RGB gradient image, 3 channels, 8 bit — tiny but deterministic */
    const gint W = 8, H = 4, CH = 3;
    guchar *img = g_malloc(W * H * CH);
    for (gint y = 0; y < H; y++)
    {
        for (gint x = 0; x < W; x++)
        {
            guchar *p = img + (y * W + x) * CH;
            p[0] = (guchar)(x * 30);
            p[1] = (guchar)(y * 60);
            p[2] = 128;
        }
    }

    /* create + init a carver on the image */
    LqrCarver *carver = lqr_carver_new(img, W, H, CH);
    check(carver != NULL, "lqr_carver_new returns non-NULL");
    if (carver == NULL)
    {
        g_free(img);
        printf("assertions=%d failures=%d\n", g_assertions, g_failures);
        return 1;
    }

    LqrRetVal init_ret = lqr_carver_init(carver, 0, 0);
    check(init_ret == LQR_OK, "lqr_carver_init returns LQR_OK");
    if (init_ret != LQR_OK)
    {
        lqr_carver_destroy(carver);
        printf("assertions=%d failures=%d\n", g_assertions, g_failures);
        return 1;
    }

    gint channels = lqr_carver_get_channels(carver);
    check(channels == CH, "lqr_carver_get_channels == 3");

    /* resize 8x4 -> 6x4 (horizontal carve, deterministic) */
    LqrRetVal resize_ret = lqr_carver_resize(carver, 6, 4);
    check(resize_ret == LQR_OK, "lqr_carver_resize(6,4) returns LQR_OK");
    if (resize_ret != LQR_OK)
    {
        lqr_carver_destroy(carver);
        printf("assertions=%d failures=%d\n", g_assertions, g_failures);
        return 1;
    }

    gint nw = lqr_carver_get_width(carver);
    gint nh = lqr_carver_get_height(carver);
    check(nw == 6, "carved width == 6");
    check(nh == 4, "carved height == 4");

    /* read the carved image back pixel by pixel and verify invariants */
    gint sx, sy;
    guchar *rgb = NULL;
    int ok = 1, n_scanned = 0;
    lqr_carver_scan_reset(carver);
    while (lqr_carver_scan(carver, &sx, &sy, &rgb))
    {
        n_scanned++;
        if (sx < 0 || sx >= nw || sy < 0 || sy >= nh)
        {
            ok = 0;
            break;
        }
        /* invariants: B channel untouched (128), G depends only on row */
        if (rgb[2] != 128 || rgb[1] != (guchar)(sy * 60))
        {
            ok = 0;
        }
    }
    check(n_scanned == nw * nh, "scan visits all 24 carved pixels");
    check(ok, "carved pixels keep B=128 and row-constant G (determinism)");

    lqr_carver_destroy(carver);

    printf("assertions=%d failures=%d\n", g_assertions, g_failures);
    return g_failures ? 1 : 0;
}
