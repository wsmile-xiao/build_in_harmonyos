#include <lcms2.h>

#include <math.h>
#include <stdio.h>

int main(void) {
    unsigned char red[3] = {255, 0, 0};
    double lab_value[3] = {0.0, 0.0, 0.0};

    if (cmsGetEncodedCMMversion() < 2190) {
        fprintf(stderr, "Unexpected Little CMS version\n");
        return 1;
    }

    cmsHPROFILE srgb = cmsCreate_sRGBProfile();
    cmsHPROFILE lab = cmsCreateLab4Profile(NULL);
    if (srgb == NULL || lab == NULL) {
        fprintf(stderr, "Profile creation failed\n");
        if (lab != NULL) {
            cmsCloseProfile(lab);
        }
        if (srgb != NULL) {
            cmsCloseProfile(srgb);
        }
        return 1;
    }

    cmsHTRANSFORM transform = cmsCreateTransform(
        srgb, TYPE_RGB_8, lab, TYPE_Lab_DBL, INTENT_PERCEPTUAL, 0
    );
    if (transform == NULL) {
        fprintf(stderr, "Transform creation failed\n");
        cmsCloseProfile(lab);
        cmsCloseProfile(srgb);
        return 1;
    }

    cmsDoTransform(transform, red, lab_value, 1);
    cmsDeleteTransform(transform);
    cmsCloseProfile(lab);
    cmsCloseProfile(srgb);

    if (!isfinite(lab_value[0]) || !isfinite(lab_value[1]) ||
        !isfinite(lab_value[2]) ||
        lab_value[0] < 40.0 || lab_value[0] > 60.0 ||
        lab_value[1] < 50.0 || lab_value[1] > 100.0 ||
        lab_value[2] < 40.0 || lab_value[2] > 100.0) {
        fprintf(stderr, "Unexpected RGB-to-Lab result: %.3f %.3f %.3f\n",
                lab_value[0], lab_value[1], lab_value[2]);
        return 1;
    }

    printf("lcms RGB-to-Lab transform: PASS (%.3f %.3f %.3f)\n",
           lab_value[0], lab_value[1], lab_value[2]);
    return 0;
}
