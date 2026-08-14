/*
 * test_package/test.c — lcms1 (Little CMS 1.x) consumer test (R34).
 *
 * 实质依赖被测包：创建 sRGB ICC profile，校验其颜色空间与设备类，
 * 并执行一次 RGB->Lab 颜色变换，验证 lcms1 API 真实可用。
 */
#include <stdio.h>
#include <stdlib.h>

#include "lcms.h"

int main(void)
{
    cmsHPROFILE sRGB = cmsCreate_sRGBProfile();
    if (sRGB == NULL) {
        fprintf(stderr, "FAIL: cmsCreate_sRGBProfile() returned NULL\n");
        return 1;
    }

    icColorSpaceSignature cs = cmsGetColorSpace(sRGB);
    if (cs != icSigRgbData) {
        fprintf(stderr, "FAIL: unexpected colorspace 0x%x\n", (unsigned)cs);
        cmsCloseProfile(sRGB);
        return 1;
    }

    icProfileClassSignature cls = cmsGetDeviceClass(sRGB);
    if (cls != icSigDisplayClass) {
        fprintf(stderr, "FAIL: unexpected device class 0x%x\n", (unsigned)cls);
        cmsCloseProfile(sRGB);
        return 1;
    }

    cmsHPROFILE lab = cmsCreateLabProfile(NULL);
    if (lab == NULL) {
        fprintf(stderr, "FAIL: cmsCreateLabProfile() returned NULL\n");
        cmsCloseProfile(sRGB);
        return 1;
    }

    cmsHTRANSFORM xf = cmsCreateTransform(
        sRGB, TYPE_RGB_8, lab, TYPE_Lab_DBL,
        INTENT_PERCEPTUAL, 0);
    if (xf == NULL) {
        fprintf(stderr, "FAIL: cmsCreateTransform() returned NULL\n");
        cmsCloseProfile(sRGB);
        cmsCloseProfile(lab);
        return 1;
    }

    unsigned char rgb[3] = {255, 128, 0};
    double lab_out[3] = {0.0, 0.0, 0.0};
    cmsDoTransform(xf, rgb, lab_out, 1);
    if (lab_out[0] <= 0.0) {
        fprintf(stderr, "FAIL: unexpected Lab L*=%f\n", lab_out[0]);
        return 1;
    }

    cmsDeleteTransform(xf);
    cmsCloseProfile(sRGB);
    cmsCloseProfile(lab);

    printf("lcms1 %d: sRGB profile + RGB->Lab transform OK\n", LCMS_VERSION);
    return 0;
}
