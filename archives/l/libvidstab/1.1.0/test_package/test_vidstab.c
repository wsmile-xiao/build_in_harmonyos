/*
 * test_vidstab.c — libvidstab 1.1.0 test_package
 *
 * Links against the real libvidstab and exercises core vid.stab APIs:
 *   - VSFrameInfo / vsFrameInfoInit            (frame metadata, field checks)
 *   - VSMotionDetectConfig / vsMotionDetectGetDefaultConfig
 *   - VSTransform null_transform / add_transforms / sub_transforms
 *       (transform composition, deterministic result assertion)
 *   - VSTransformations init / cleanup lifecycle
 *   - full VSMotionDetect create -> detect -> cleanup lifecycle on two
 *     synthesized flat GRAY8 frame buffers held in memory
 *
 * No FFmpeg, no GUI, no file I/O — pure C core API with deterministic checks.
 * Return 0 on success, 1 on any failure.
 */

#include <libvidstab.h>
/* transformtype_operations.h is an installed public header (every header in
 * src is globbed and installed by CMake) that is not pulled in by the
 * libvidstab.h umbrella; it declares null_transform / add_transforms /
 * sub_transforms / new_transform. */
#include <transformtype_operations.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* tiny test framework */
static int g_fail = 0;
#define CHECK(cond, msg) do { \
    if (!(cond)) { printf("FAIL: %s\n", msg); g_fail = 1; } \
    else { printf("ok:   %s\n", msg); } \
} while (0)

int main(void)
{
    int rc;
    printf("=== libvidstab %s test_package ===\n", LIBVIDSTAB_VERSION);

    /* ---- 1. Frame info (VSFrameInfo) init ----------------------------- */
    /* vsFrameInfoInit(fi, width, height, pFormat) — width/height BEFORE format.
     * Note: unlike most vid.stab int-returning APIs (which use the VS_OK=0 /
     * VS_ERROR=-1 sentinels), vsFrameInfoInit() returns a *boolean*: 1 on
     * success, 0 on failure (unknown pixel format).  So the success check
     * here is `rc != 0` (== 1), NOT `rc == VS_OK`. */
    VSFrameInfo fi;
    rc = vsFrameInfoInit(&fi, 64, 32, PF_GRAY8);
    CHECK(rc != 0, "vsFrameInfoInit(64x32, PF_GRAY8) succeeds (rc==1)");
    CHECK(fi.width == 64 && fi.height == 32, "fi.width==64 && fi.height==32");
    CHECK(fi.pFormat == PF_GRAY8, "fi.pFormat == PF_GRAY8");
    CHECK(fi.planes == 1, "fi.planes == 1 (GRAY8 is single-plane)");
    CHECK(fi.bytesPerPixel == 1, "fi.bytesPerPixel == 1 (GRAY8)");

    /* ---- 2. Motion-detect config init -------------------------------- */
    VSMotionDetectConfig mdconf = vsMotionDetectGetDefaultConfig("test_vidstab");
    CHECK(mdconf.shakiness > 0, "mdconf.shakiness > 0 (default config set)");
    CHECK(mdconf.accuracy > 0, "mdconf.accuracy > 0 (default config set)");
    CHECK(mdconf.stepSize == 6, "mdconf.stepSize == 6 (upstream default)");
    CHECK(mdconf.modName != NULL, "mdconf.modName != NULL");

    /* ---- 3. Transform composition (snake_case transform ops) --------- */
    /* null + null == null : deterministic identity check. */
    VSTransform t_null_a = null_transform();
    VSTransform t_null_b = null_transform();
    CHECK(t_null_a.x == 0.0 && t_null_a.y == 0.0 && t_null_a.alpha == 0.0 &&
          t_null_a.zoom == 0.0, "null_transform() == all-zero transform");

    VSTransform t_sum = add_transforms(&t_null_a, &t_null_b);
    CHECK(t_sum.x == 0.0 && t_sum.y == 0.0 && t_sum.alpha == 0.0 &&
          t_sum.zoom == 0.0,
          "add_transforms(null, null) == null");

    /* a known shift added to its negation must yield exactly zero. */
    VSTransform t_pos = new_transform(5.0, -3.0, 0.0, 0.0, 0.0, 0.0, 0);
    VSTransform t_neg = new_transform(-5.0, 3.0, 0.0, 0.0, 0.0, 0.0, 0);
    VSTransform t_zero = add_transforms(&t_pos, &t_neg);
    CHECK(t_zero.x == 0.0 && t_zero.y == 0.0,
          "add_transforms(+shift, -shift) == null");

    /* sub_transforms(a, a) == null */
    VSTransform t_diff = sub_transforms(&t_pos, &t_pos);
    CHECK(t_diff.x == 0.0 && t_diff.y == 0.0,
          "sub_transforms(t, t) == null");

    /* ---- 4. Transformations container lifecycle ---------------------- */
    /* vsTransformationsInit takes a single VSTransformations* argument. */
    VSTransformations trans;
    vsTransformationsInit(&trans);
    CHECK(trans.ts == NULL && trans.len == 0, "vsTransformationsInit sets empty array");
    vsTransformationsCleanup(&trans);
    CHECK(1, "vsTransformationsCleanup OK");

    /* ---- 5. Full motion-detect lifecycle on 2 flat GRAY8 frames ------ */
    /* Two identical flat frames: no motion. vsMotionDetection stores the
       previous frame internally, so we call it twice (first seeds prev). */
    size_t fsize = (size_t)fi.width * (size_t)fi.height * (size_t)fi.bytesPerPixel;
    unsigned char *buf1 = (unsigned char *)calloc(fsize, 1);
    unsigned char *buf2 = (unsigned char *)calloc(fsize, 1);
    CHECK(buf1 != NULL && buf2 != NULL, "allocated 2 flat GRAY8 frame buffers");
    /* paint a tiny non-uniform patch so measurement fields have contrast */
    if (fsize > 4) {
        buf1[0] = 200; buf1[1] = 10;
        buf2[0] = 200; buf2[1] = 10;
    }

    VSFrame frame1, frame2;
    vsFrameFillFromBuffer(&frame1, buf1, &fi);
    vsFrameFillFromBuffer(&frame2, buf2, &fi);

    VSMotionDetect md;
    rc = vsMotionDetectInit(&md, &mdconf, &fi);
    CHECK(rc == VS_OK, "vsMotionDetectInit == VS_OK");

    LocalMotions lm1, lm2;
    memset(&lm1, 0, sizeof(lm1));
    memset(&lm2, 0, sizeof(lm2));
    rc = vsMotionDetection(&md, &lm1, &frame1);
    CHECK(rc == VS_OK, "vsMotionDetection(frame1) == VS_OK");
    rc = vsMotionDetection(&md, &lm2, &frame2);
    CHECK(rc == VS_OK, "vsMotionDetection(frame2) == VS_OK");

    /* clean up the locally-returned motion vectors (own their elements) */
    vs_vector_del(&lm1);
    vs_vector_del(&lm2);

    vsMotionDetectionCleanup(&md);
    CHECK(1, "vsMotionDetectionCleanup OK");

    free(buf1);
    free(buf2);

    /* ---- 6. version --------------------------------------------------- */
    CHECK(LIBVIDSTAB_VERSION != NULL && LIBVIDSTAB_VERSION[0] != '\0',
          "LIBVIDSTAB_VERSION macro non-empty");
    printf("LIBVIDSTAB_VERSION = %s\n", LIBVIDSTAB_VERSION);

    printf("=== %s ===\n", g_fail ? "FAILED" : "ALL OK");
    return g_fail;
}
