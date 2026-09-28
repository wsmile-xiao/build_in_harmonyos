/* Consumer test for the installed mrcal package.
 *
 * Uses the installed public header mrcal.h and libmrcal.so to exercise the
 * lens-model API (the same surface upstream's pure-C test programs cover). */
#include <stdio.h>
#include <string.h>

#include "mrcal.h"

static int checks = 0;
static int fails = 0;

#define CHECK(cond, msg) do { \
    checks++; \
    if (!(cond)) { fails++; printf("FAIL: %s\n", (msg)); } \
} while (0)

int main(void)
{
    mrcal_lensmodel_t m;
    char name[128];

    memset(&m, 0, sizeof(m));

    m.type = MRCAL_LENSMODEL_CAHVOR;
    CHECK(mrcal_lensmodel_num_params(&m) == 9, "CAHVOR has 9 parameters");
    CHECK(mrcal_lensmodel_name(name, sizeof(name), &m), "CAHVOR name() succeeds");
    CHECK(strcmp(name, "LENSMODEL_CAHVOR") == 0, "CAHVOR name text");

    m.type = MRCAL_LENSMODEL_OPENCV8;
    CHECK(mrcal_lensmodel_num_params(&m) == 12, "OPENCV8 has 12 parameters");
    CHECK(mrcal_lensmodel_name(name, sizeof(name), &m), "OPENCV8 name() succeeds");
    CHECK(strcmp(name, "LENSMODEL_OPENCV8") == 0, "OPENCV8 name text");

    CHECK(mrcal_lensmodel_type_from_name("LENSMODEL_OPENCV4") == MRCAL_LENSMODEL_OPENCV4,
          "type_from_name(OPENCV4)");
    CHECK(mrcal_lensmodel_type_from_name("LENSMODEL_CAHVOR") == MRCAL_LENSMODEL_CAHVOR,
          "type_from_name(CAHVOR)");

    m.type = MRCAL_LENSMODEL_SPLINED_STEREOGRAPHIC;
    m.LENSMODEL_SPLINED_STEREOGRAPHIC__config.order = 3;
    m.LENSMODEL_SPLINED_STEREOGRAPHIC__config.Nx = 30;
    m.LENSMODEL_SPLINED_STEREOGRAPHIC__config.Ny = 20;
    m.LENSMODEL_SPLINED_STEREOGRAPHIC__config.fov_x_deg = 200;
    CHECK(mrcal_lensmodel_num_params(&m) == 4 + 30 * 20 * 2,
          "splined stereographic parameter count");

    printf("MRCAL_CHECK_SUMMARY checks=%d fails=%d\n", checks, fails);
    return fails == 0 ? 0 : 1;
}
