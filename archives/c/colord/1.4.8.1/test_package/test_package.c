#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Include colord public headers (libcolord) */
#include <colord.h>

/*
 * EDID blob from upstream colord test data
 * (data/tests/LG-L225W-External.bin, 128-byte base EDID).
 * PNP ID = "GSM" (LG), monitor name = "L225W", checksum as asserted by the
 * upstream colord-test-private /colord/edid case.
 */
static const unsigned char edid_lg[] = {
    0x00, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x00, 0x1e, 0x6d, 0x63, 0x56, 0x5e, 0x86, 0x00, 0x00,
    0x0c, 0x11, 0x01, 0x03, 0xea, 0x2f, 0x1e, 0x78, 0xea, 0xd4, 0x25, 0xa4, 0x55, 0x49, 0x9b, 0x27,
    0x13, 0x50, 0x54, 0xa7, 0x6b, 0x80, 0x95, 0x0f, 0x95, 0x00, 0x81, 0x80, 0x81, 0x40, 0x71, 0x4f,
    0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x7c, 0x2e, 0x90, 0xa0, 0x60, 0x1a, 0x1e, 0x40, 0x30, 0x20,
    0x36, 0x00, 0xda, 0x28, 0x11, 0x00, 0x00, 0x1a, 0x21, 0x39, 0x90, 0x30, 0x62, 0x1a, 0x27, 0x40,
    0x68, 0xb0, 0x36, 0x00, 0xda, 0x28, 0x11, 0x00, 0x00, 0x1c, 0x00, 0x00, 0x00, 0xfd, 0x00, 0x38,
    0x4b, 0x1c, 0x53, 0x0f, 0x00, 0x0a, 0x20, 0x20, 0x20, 0x20, 0x20, 0x20, 0x00, 0x00, 0x00, 0xfc,
    0x00, 0x4c, 0x32, 0x32, 0x35, 0x57, 0x00, 0x0a, 0x20, 0x20, 0x20, 0x20, 0x20, 0x20, 0x00, 0x74,
};

/* Generic consumer API smoke test: CdColorRGB */
static int test_cd_color_rgb(void)
{
    CdColorRGB *rgb = cd_color_rgb_new();
    if (rgb == NULL) {
        fprintf(stderr, "FAIL: cd_color_rgb_new() returned NULL\n");
        return 1;
    }

    cd_color_rgb_set(rgb, 0.5, 0.25, 0.75);
    if (rgb->R != 0.5 || rgb->G != 0.25 || rgb->B != 0.75) {
        fprintf(stderr, "FAIL: RGB values mismatch\n");
        cd_color_rgb_free(rgb);
        return 1;
    }

    printf("PASS: CdColorRGB API working (RGB(%.2f, %.2f, %.2f))\n",
           rgb->R, rgb->G, rgb->B);
    cd_color_rgb_free(rgb);
    return 0;
}

/* Generic consumer API smoke test: CdIcc */
static int test_cd_icc(void)
{
    CdIcc *icc = cd_icc_new();
    gboolean ret;
    GError *error = NULL;

    if (icc == NULL) {
        fprintf(stderr, "FAIL: cd_icc_new() returned NULL\n");
        return 1;
    }
    GFile *nope = g_file_new_for_path("/nonexistent/nope.icc");
    ret = cd_icc_load_file(icc, nope, CD_ICC_LOAD_FLAGS_NONE, NULL, &error);
    g_object_unref(nope);
    /* expected to fail cleanly on a missing file, not crash */
    if (ret) {
        fprintf(stderr, "FAIL: cd_icc_load_file on missing file unexpectedly succeeded\n");
        g_object_unref(icc);
        return 1;
    }
    if (error == NULL) {
        fprintf(stderr, "FAIL: cd_icc_load_file reported no error for missing file\n");
        g_object_unref(icc);
        return 1;
    }
    printf("PASS: CdIcc API working (missing file -> error: %s)\n", error->message);
    g_error_free(error);
    g_object_unref(icc);
    return 0;
}

/*
 * OHOS-specific test: cd_edid behaviour on a platform without libudev.
 *
 * colord is adapted so that on OHOS (no udev hwdb) the EDID parser is built
 * with HAVE_LIBUDEV undefined: cd_edid_parse() must still extract monitor
 * name / PNP ID / checksum from a raw EDID blob, and
 * cd_edid_get_vendor_name() must return NULL (vendor-name resolution
 * depends on the udev hwdb database which does not exist on OHOS).
 */
static int test_edid_no_udev(void)
{
    CdEdid *edid = cd_edid_new();
    GBytes *data = NULL;
    GError *error = NULL;
    const gchar *s;

    if (edid == NULL) {
        fprintf(stderr, "FAIL: cd_edid_new() returned NULL\n");
        return 1;
    }

    data = g_bytes_new_static(edid_lg, sizeof(edid_lg));
    if (!cd_edid_parse(edid, data, &error)) {
        fprintf(stderr, "FAIL: cd_edid_parse failed: %s\n",
                error ? error->message : "no error set");
        if (error)
            g_error_free(error);
        g_bytes_unref(data);
        g_object_unref(edid);
        return 1;
    }

    s = cd_edid_get_monitor_name(edid);
    if (s == NULL || strcmp(s, "L225W") != 0) {
        fprintf(stderr, "FAIL: monitor name = '%s' (expected 'L225W')\n",
                s ? s : "(null)");
        g_bytes_unref(data);
        g_object_unref(edid);
        return 1;
    }

    s = cd_edid_get_pnp_id(edid);
    if (s == NULL || strcmp(s, "GSM") != 0) {
        fprintf(stderr, "FAIL: PNP ID = '%s' (expected 'GSM')\n",
                s ? s : "(null)");
        g_bytes_unref(data);
        g_object_unref(edid);
        return 1;
    }

    s = cd_edid_get_checksum(edid);
    if (s == NULL || strcmp(s, "0bb44865bb29984a4bae620656c31368") != 0) {
        fprintf(stderr, "FAIL: EDID checksum = '%s' (expected "
                "'0bb44865bb29984a4bae620656c31368')\n", s ? s : "(null)");
        g_bytes_unref(data);
        g_object_unref(edid);
        return 1;
    }

#if defined(__OHOS__) || defined(__OHOS_FAMILY__)
    /* On OHOS there is no udev hwdb: vendor name must be NULL. */
    s = cd_edid_get_vendor_name(edid);
    if (s != NULL) {
        fprintf(stderr, "FAIL: OHOS vendor name = '%s' (expected NULL, no udev "
                "hwdb on this platform)\n", s);
        g_bytes_unref(data);
        g_object_unref(edid);
        return 1;
    }
    printf("PASS: OHOS no-udev edid path verified (vendor=NULL, "
           "monitor/PNP/checksum parsed)\n");
#else
    printf("PASS: EDID parsed on non-OHOS build (vendor lookup via hwdb)\n");
#endif

    g_bytes_unref(data);
    g_object_unref(edid);
    return 0;
}

int main(void)
{
    int rc = 0;

    rc |= test_cd_color_rgb();
    rc |= test_cd_icc();
    rc |= test_edid_no_udev();

    if (rc == 0) {
        printf("colord test_package: all tests passed\n");
        return 0;
    }
    fprintf(stderr, "colord test_package: %d test(s) failed\n", rc);
    return 1;
}
