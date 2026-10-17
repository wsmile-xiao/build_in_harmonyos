/* vips 8.18.4.1 test_package.
 *
 * Beyond the core operation check inherited from 8.18.4, this verifies the
 * whole point of this adaptation revision: that the JPEG and PNG loaders and
 * savers are actually compiled into the package. It round-trips a generated
 * image through both codecs and asserts the pixels survive.
 */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <vips/vips.h>

#define W 16
#define H 16
/* constant pixel written into the source image, per band */
#define PIX_R 10.0
#define PIX_G 20.0
#define PIX_B 30.0

/* vips_foreign_find_load() returns a const, internally-owned loader name such
 * as "VipsForeignLoadJpegFile" — it must NOT be freed, and the codec appears
 * capitalised, so match it case-insensitively. */
static int loader_matches(const char *loader, const char *want) {
    if (!loader) {
        return 0;
    }
    char *lower = g_ascii_strdown(loader, -1);
    int ok = strstr(lower, want) != NULL;
    g_free(lower);
    return ok;
}

static int check_pixel(VipsImage *im, const char *label, int exact) {
    if (vips_image_wio_input(im)) {
        fprintf(stderr, "%s: image not loadable into memory\n", label);
        return 1;
    }
    if (vips_image_get_width(im) != W || vips_image_get_height(im) != H) {
        fprintf(stderr, "%s: unexpected size %dx%d\n", label,
                vips_image_get_width(im), vips_image_get_height(im));
        return 1;
    }
    if (vips_image_get_bands(im) != 3) {
        fprintf(stderr, "%s: unexpected band count %d\n", label,
                vips_image_get_bands(im));
        return 1;
    }

    const VipsPel *p = VIPS_IMAGE_ADDR(im, W / 2, H / 2);
    const double expect[3] = {PIX_R, PIX_G, PIX_B};
    const int got[3] = {p[0], p[1], p[2]};
    /* JPEG is lossy and quantised, so allow a small tolerance; PNG is exact. */
    const int tol = exact ? 0 : 8;
    for (int i = 0; i < 3; i++) {
        if (abs(got[i] - (int)expect[i]) > tol) {
            fprintf(stderr, "%s: band %d is %d, expected %d (tol %d)\n",
                    label, i, got[i], (int)expect[i], tol);
            return 1;
        }
    }
    return 0;
}

int main(int argc, char **argv) {
    if (VIPS_INIT(argv[0])) {
        vips_error_exit(NULL);
    }

    /* The 8.18.4 smoke check: core ops still work. */
    VipsImage *image = vips_image_new_matrixv(2, 2, 1.0, 2.0, 3.0, 4.0);
    if (!image) {
        vips_shutdown();
        return 1;
    }
    double average = 0.0;
    if (vips_avg(image, &average, NULL)) {
        g_object_unref(image);
        vips_shutdown();
        return 1;
    }
    g_object_unref(image);
    if (fabs(average - 2.5) > 0.000001) {
        fprintf(stderr, "unexpected average: %.12f\n", average);
        vips_shutdown();
        return 1;
    }

    /* Build a WxH 3-band uchar image with a constant colour. */
    VipsImage *black = NULL;
    if (vips_black(&black, W, H, "bands", 3, NULL)) {
        vips_shutdown();
        return 1;
    }
    VipsImage *linear = NULL;
    double a[3] = {1.0, 1.0, 1.0};
    double b[3] = {PIX_R, PIX_G, PIX_B};
    if (vips_linear(black, &linear, a, b, 3, NULL)) {
        g_object_unref(black);
        vips_shutdown();
        return 1;
    }
    g_object_unref(black);
    VipsImage *src = NULL;
    if (vips_cast(linear, &src, VIPS_FORMAT_UCHAR, NULL)) {
        g_object_unref(linear);
        vips_shutdown();
        return 1;
    }
    g_object_unref(linear);

    int failed = 0;

    /* JPEG: save, confirm the loader claims the file, then read it back. */
    if (vips_jpegsave(src, "test_vips.jpg", "Q", 95, NULL)) {
        fprintf(stderr, "jpegsave failed — JPEG saver missing?\n");
        failed = 1;
    }
    if (!failed) {
        const char *loader = vips_foreign_find_load("test_vips.jpg");
        if (!loader_matches(loader, "jpeg")) {
            fprintf(stderr, "no JPEG loader for test_vips.jpg (got '%s')\n",
                    loader ? loader : "(none)");
            failed = 1;
        }
    }
    if (!failed) {
        VipsImage *jpg = vips_image_new_from_file("test_vips.jpg", NULL);
        if (!jpg) {
            fprintf(stderr, "failed to reload test_vips.jpg\n");
            failed = 1;
        } else {
            failed = check_pixel(jpg, "jpeg round-trip", 0);
            g_object_unref(jpg);
        }
    }
    remove("test_vips.jpg");

    /* PNG: same thing, but the values must come back bit-exact. */
    if (!failed && vips_pngsave(src, "test_vips.png", NULL)) {
        fprintf(stderr, "pngsave failed — PNG saver missing?\n");
        failed = 1;
    }
    if (!failed) {
        const char *loader = vips_foreign_find_load("test_vips.png");
        if (!loader_matches(loader, "png")) {
            fprintf(stderr, "no PNG loader for test_vips.png (got '%s')\n",
                    loader ? loader : "(none)");
            failed = 1;
        }
    }
    if (!failed) {
        VipsImage *png = vips_image_new_from_file("test_vips.png", NULL);
        if (!png) {
            fprintf(stderr, "failed to reload test_vips.png\n");
            failed = 1;
        } else {
            failed = check_pixel(png, "png round-trip", 1);
            g_object_unref(png);
        }
    }
    remove("test_vips.png");

    if (!failed) {
        printf("vips %s: jpeg + png load/save verified\n",
               vips_version_string());
    }

    g_object_unref(src);
    vips_shutdown();
    return failed;
}
