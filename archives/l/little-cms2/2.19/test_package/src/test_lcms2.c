/* Little CMS 2 consumer test.
 *
 * Links the installed liblcms2 and drives the public <lcms2.h> API through a
 * real colour-management round trip: build an sRGB profile and a Lab profile,
 * create a transform between them, and check that known colours land where
 * colour science says they must (R34: the test exercises the package under
 * test rather than merely linking it).
 */

#include <lcms2.h>

#include <math.h>
#include <stdio.h>

static int failures = 0;

static void check(int ok, const char *what)
{
    printf("%s %s\n", ok ? "ok  " : "FAIL", what);
    if (!ok) {
        ++failures;
    }
}

int main(void)
{
    cmsHPROFILE srgb;
    cmsHPROFILE lab;
    cmsHTRANSFORM xform;
    unsigned char white[3] = {255, 255, 255};
    unsigned char black[3] = {0, 0, 0};
    cmsCIELab white_lab, black_lab;
    cmsUInt32Number size;

    /* 1. the runtime version reported by the library itself */
    check(cmsGetEncodedCMMversion() == LCMS_VERSION,
          "runtime cmsGetEncodedCMMversion() == header LCMS_VERSION");
    check(cmsGetEncodedCMMversion() == 2190, "encoded version is 2190 (2.19)");

    /* 2. profile construction */
    srgb = cmsCreate_sRGBProfile();
    check(srgb != NULL, "cmsCreate_sRGBProfile()");
    if (srgb == NULL) {
        fprintf(stderr, "cannot continue without an sRGB profile\n");
        return 1;
    }
    check(cmsGetColorSpace(srgb) == cmsSigRgbData, "sRGB colour space is RGB");

    size = cmsGetProfileInfoASCII(srgb, cmsInfoDescription, "en", "US", NULL, 0);
    check(size > 0, "profile description tag is readable");

    lab = cmsCreateLab4Profile(NULL);
    check(lab != NULL, "cmsCreateLab4Profile()");
    if (lab == NULL) {
        return 1;
    }

    /* 3. transform between the two profiles */
    xform = cmsCreateTransform(srgb, TYPE_RGB_8, lab, TYPE_Lab_DBL,
                               INTENT_PERCEPTUAL, 0);
    check(xform != NULL, "cmsCreateTransform(RGB_8 -> Lab_DBL)");
    if (xform == NULL) {
        return 1;
    }

    /* 4. white must map to L* = 100, a* = b* = 0 */
    cmsDoTransform(xform, white, &white_lab, 1);
    check(white_lab.L > 99.0 && white_lab.L <= 100.01,
          "white maps to L* ~ 100");
    check(fabs(white_lab.a) < 1.0 && fabs(white_lab.b) < 1.0,
          "white maps to a* ~ b* ~ 0");

    /* 5. black must map to L* ~ 0 */
    cmsDoTransform(xform, black, &black_lab, 1);
    check(black_lab.L < 1.0, "black maps to L* ~ 0");

    /* 6. the transform must be monotonic in lightness */
    check(white_lab.L > black_lab.L, "white is lighter than black");

    cmsDeleteTransform(xform);
    cmsCloseProfile(lab);
    cmsCloseProfile(srgb);

    if (failures != 0) {
        fprintf(stderr, "%d little-cms2 consumer check(s) FAILED\n", failures);
        return 1;
    }
    printf("all little-cms2 consumer checks passed\n");
    return 0;
}
