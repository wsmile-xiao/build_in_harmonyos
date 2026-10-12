#include <stdio.h>
#include <stdlib.h>

/* Include colord public headers */
#include <colord.h>

int main(void) {
    /* ---- Test 1: CdColorRGB basic API (plain C struct, no GObject) ---- */
    CdColorRGB *rgb = cd_color_rgb_new();
    if (rgb == NULL) {
        fprintf(stderr, "FAIL: cd_color_rgb_new() returned NULL\n");
        return 1;
    }

    cd_color_rgb_set(rgb, 0.5, 0.25, 0.75);
    if (rgb->R != 0.5 || rgb->G != 0.25 || rgb->B != 0.75) {
        fprintf(stderr, "FAIL: CdColorRGB values mismatch\n");
        cd_color_rgb_free(rgb);
        return 1;
    }
    printf("PASS: CdColorRGB set/get RGB(%.2f, %.2f, %.2f)\n",
           rgb->R, rgb->G, rgb->B);
    cd_color_rgb_free(rgb);

    /* ---- Test 2: CdColorRGB math helpers (pure C, no GObject) ---- */
    CdColorRGB a = {0.5f, 0.0f, 0.0f};
    CdColorRGB b = {0.0f, 1.0f, 0.0f};
    CdColorRGB out;
    cd_color_rgb_interpolate(&a, &b, 0.5f, &out);
    if (out.R < 0.24f || out.R > 0.26f ||
        out.G < 0.49f || out.G > 0.51f ||
        out.B < -0.01f || out.B > 0.01f) {
        fprintf(stderr, "FAIL: cd_color_rgb_interpolate result out of range\n");
        return 1;
    }
    printf("PASS: CdColorRGB interpolate (%.2f, %.2f, %.2f)\n",
           out.R, out.G, out.B);

    /* ---- Test 3: CdIcc API (GObject) ----
     * NOTE: On OHOS, libcolord.so embeds a static copy of glib while the
     * test binary links another static glib. GObject instances created by
     * the library (cd_icc_new) must therefore be released inside the
     * library, not via g_object_unref() in the test binary (cross-copy
     * GType table mismatch would SIGSEGV). We exercise the library-side
     * API and let the process exit reclaim the object.
     */
    CdIcc *icc = cd_icc_new();
    if (icc == NULL) {
        fprintf(stderr, "FAIL: cd_icc_new() returned NULL\n");
        return 1;
    }

    /* add metadata key/value and read it back (library-side GType table) */
    cd_icc_add_metadata(icc, "KEY1", "VALUE1");
    cd_icc_add_metadata(icc, "KEY2", "VALUE2");
    if (g_strcmp0(cd_icc_get_metadata_item(icc, "KEY1"), "VALUE1") != 0) {
        fprintf(stderr, "FAIL: cd_icc_get_metadata_item(KEY1) mismatch\n");
        return 1;
    }
    printf("PASS: CdIcc metadata KEY1=VALUE1\n");

    /* version accessor: a freshly created CdIcc has no loaded profile,
     * so get_version() must be >= 0.0 and stable across calls */
    {
        gdouble v1 = cd_icc_get_version(icc);
        gdouble v2 = cd_icc_get_version(icc);
        if (v1 != v2 || v1 < 0.0) {
            fprintf(stderr, "FAIL: cd_icc_get_version() unstable (%f vs %f)\n", v1, v2);
            return 1;
        }
        printf("PASS: CdIcc version accessor stable (%.1f)\n", v1);
    }

    printf("test_package: libcolord 1.4.8 API works correctly\n");
    return 0;
}
