/* test_imageworsener.c — test_package consumer test for imageworsener.
 *
 * Calls the real public C API from <imagew.h> (version, context
 * lifecycle, format detection, colorspace helpers, parse helpers).
 * Each check prints one "HMBS_CHECK: <name> PASS" line; the conanfile
 * counts those lines for the HMBS_TEST_PACKAGE_RESULT machine-evidence
 * marker. Exit code is 0 only if all checks pass.
 */
#define IW_INCLUDE_UTIL_FUNCTIONS /* expose iw_parse_number() decls */

#include <imagew.h>

#include <math.h>
#include <stdio.h>
#include <string.h>

static int g_failed = 0;

#define CHECK(name, cond) do { \
    if (cond) { \
        printf("HMBS_CHECK: %s PASS\n", name); \
    } else { \
        printf("HMBS_CHECK: %s FAIL\n", name); \
        g_failed++; \
    } \
} while (0)

int main(void) {
    char buf[128];
    struct iw_context *ctx;
    struct iw_init_params params;
    struct iw_csdescr cs;

    /* 1. Version matches the 1.3.5 header. */
    CHECK("version_int", iw_get_version_int() == IW_VERSION_INT);
    CHECK("version_int_value", iw_get_version_int() == 0x010305);

    /* 2. Version string renders as 1.3.5. */
    memset(buf, 0, sizeof(buf));
    CHECK("version_string",
          iw_get_version_string(NULL, buf, (int)sizeof(buf)) != NULL
          && strcmp(buf, "1.3.5") == 0);

    /* 3. Context lifecycle with NULL params. */
    ctx = iw_create_context(NULL);
    CHECK("create_null", ctx != NULL);
    CHECK("errorflag_fresh", ctx != NULL && iw_get_errorflag(ctx) == 0);
    iw_destroy_context(ctx);
    iw_destroy_context(NULL); /* must tolerate NULL */
    printf("HMBS_CHECK: destroy_null PASS\n");

    /* 4. Context lifecycle with explicit params. */
    memset(&params, 0, sizeof(params));
    params.api_version = IW_VERSION_INT;
    ctx = iw_create_context(&params);
    CHECK("create_params", ctx != NULL);
    if (ctx != NULL) {
        iw_set_value(ctx, IW_VAL_DISABLE_GAMMA, 1);
        CHECK("set_get_value",
              iw_get_value(ctx, IW_VAL_DISABLE_GAMMA) == 1);
        iw_destroy_context(ctx);
    } else {
        g_failed += 2;
        printf("HMBS_CHECK: set_get_value FAIL\n");
    }

    /* 5. Format detection from filename extensions. */
    CHECK("fmt_png", iw_detect_fmt_from_filename("a.png") == IW_FORMAT_PNG);
    CHECK("fmt_jpg", iw_detect_fmt_from_filename("a.jpg") == IW_FORMAT_JPEG);
    CHECK("fmt_jpeg",
          iw_detect_fmt_from_filename("a.jpeg") == IW_FORMAT_JPEG);
    CHECK("fmt_bmp", iw_detect_fmt_from_filename("a.bmp") == IW_FORMAT_BMP);
    CHECK("fmt_webp",
          iw_detect_fmt_from_filename("a.webp") == IW_FORMAT_WEBP);
    CHECK("fmt_gif", iw_detect_fmt_from_filename("a.gif") == IW_FORMAT_GIF);
    CHECK("fmt_unknown",
          iw_detect_fmt_from_filename("a.zzz") == IW_FORMAT_UNKNOWN);
    CHECK("fmt_noext",
          iw_detect_fmt_from_filename("noext") == IW_FORMAT_UNKNOWN);

    /* 6. Format names. */
    CHECK("name_png", iw_get_fmt_name(IW_FORMAT_PNG) != NULL
          && strcmp(iw_get_fmt_name(IW_FORMAT_PNG), "PNG") == 0);
    CHECK("name_jpeg", iw_get_fmt_name(IW_FORMAT_JPEG) != NULL
          && strcmp(iw_get_fmt_name(IW_FORMAT_JPEG), "JPEG") == 0);
    CHECK("name_bmp", iw_get_fmt_name(IW_FORMAT_BMP) != NULL
          && strcmp(iw_get_fmt_name(IW_FORMAT_BMP), "BMP") == 0);
    CHECK("name_webp", iw_get_fmt_name(IW_FORMAT_WEBP) != NULL
          && strcmp(iw_get_fmt_name(IW_FORMAT_WEBP), "WebP") == 0);
    CHECK("name_gif", iw_get_fmt_name(IW_FORMAT_GIF) != NULL
          && strcmp(iw_get_fmt_name(IW_FORMAT_GIF), "GIF") == 0);
    CHECK("name_unknown", iw_get_fmt_name(IW_FORMAT_UNKNOWN) == NULL);

    /* 7. Format sniffing from magic bytes. */
    {
        static const iw_byte png_sig[16] =
            {0x89, 'P', 'N', 'G', 0x0d, 0x0a, 0x1a, 0x0a,
             0, 0, 0, 0, 0, 0, 0, 0};
        static const iw_byte jpg_sig[16] =
            {0xff, 0xd8, 0xff, 0xe0, 0, 0, 0, 0,
             0, 0, 0, 0, 0, 0, 0, 0};
        static const iw_byte gif_sig[16] =
            {'G', 'I', 'F', '8', '9', 'a', 0, 0,
             0, 0, 0, 0, 0, 0, 0, 0};
        static const iw_byte bmp_sig[16] =
            {'B', 'M', 0, 0, 0, 0, 0, 0,
             0, 0, 0, 0, 0, 0, 0, 0};
        CHECK("magic_png",
              iw_detect_fmt_of_file(png_sig, sizeof(png_sig))
              == IW_FORMAT_PNG);
        CHECK("magic_jpg",
              iw_detect_fmt_of_file(jpg_sig, sizeof(jpg_sig))
              == IW_FORMAT_JPEG);
        CHECK("magic_gif",
              iw_detect_fmt_of_file(gif_sig, sizeof(gif_sig))
              == IW_FORMAT_GIF);
        CHECK("magic_bmp",
              iw_detect_fmt_of_file(bmp_sig, sizeof(bmp_sig))
              == IW_FORMAT_BMP);
    }

    /* 8-9. Enabled format support (all optional deps are required). */
    CHECK("in_png", iw_is_input_fmt_supported(IW_FORMAT_PNG) != 0);
    CHECK("in_jpeg", iw_is_input_fmt_supported(IW_FORMAT_JPEG) != 0);
    CHECK("in_webp", iw_is_input_fmt_supported(IW_FORMAT_WEBP) != 0);
    CHECK("in_bmp", iw_is_input_fmt_supported(IW_FORMAT_BMP) != 0);
    CHECK("in_gif", iw_is_input_fmt_supported(IW_FORMAT_GIF) != 0);
    CHECK("out_png", iw_is_output_fmt_supported(IW_FORMAT_PNG) != 0);
    CHECK("out_bmp", iw_is_output_fmt_supported(IW_FORMAT_BMP) != 0);

    /* 10. Channel counts per image type. */
    CHECK("ch_rgba", iw_imgtype_num_channels(IW_IMGTYPE_RGBA) == 4);
    CHECK("ch_rgb", iw_imgtype_num_channels(IW_IMGTYPE_RGB) == 3);
    CHECK("ch_graya", iw_imgtype_num_channels(IW_IMGTYPE_GRAYA) == 2);
    CHECK("ch_gray", iw_imgtype_num_channels(IW_IMGTYPE_GRAY) == 1);

    /* 11. Bytes-per-row rounds up to whole bytes. */
    CHECK("bpr_24bpp", iw_calc_bytesperrow(10, 24) == 30);
    CHECK("bpr_1bpp_roundup", iw_calc_bytesperrow(9, 1) == 2);
    CHECK("bpr_1bpp_exact", iw_calc_bytesperrow(8, 1) == 1);

    /* 12. Host endianness probe (aarch64 is little-endian). */
    CHECK("endian", iw_get_host_endianness() == IW_ENDIAN_LITTLE);

    /* 13. Linked third-party library version strings are present. */
    memset(buf, 0, sizeof(buf));
    CHECK("ver_libpng",
          iw_get_libpng_version_string(buf, (int)sizeof(buf)) != NULL
          && buf[0] != '\0');
    memset(buf, 0, sizeof(buf));
    CHECK("ver_libjpeg",
          iw_get_libjpeg_version_string(buf, (int)sizeof(buf)) != NULL
          && buf[0] != '\0');
    memset(buf, 0, sizeof(buf));
    CHECK("ver_zlib",
          iw_get_zlib_version_string(buf, (int)sizeof(buf)) != NULL
          && buf[0] != '\0');

    /* 14. Number parsing helpers. */
    CHECK("parse_number", fabs(iw_parse_number("2.5") - 2.5) < 1e-9);
    CHECK("parse_int", iw_parse_int("3.7") == 4);

    /* 15. Linear colorspace is the identity for sample conversion. */
    iw_make_linear_csdescr(&cs);
    CHECK("linear_identity",
          fabs(iw_convert_sample_to_linear(0.5, &cs) - 0.5) < 1e-12);
    iw_make_srgb_csdescr_2(&cs);
    CHECK("srgb_white",
          fabs(iw_convert_sample_to_linear(1.0, &cs) - 1.0) < 1e-9);

    if (g_failed == 0) {
        printf("HMBS_TEST_SUMMARY: all checks passed\n");
    } else {
        printf("HMBS_TEST_SUMMARY: %d check(s) failed\n", g_failed);
    }
    return g_failed == 0 ? 0 : 1;
}
