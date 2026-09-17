// SPDX-License-Identifier: LGPL-3.0
// Test package for libccp4 - exercises real ccp4c API (R34 compliant)

#include <ccp4/ccp4_unitcell.h>
#include <ccp4/ccp4_general.h>
#include <ccp4/ccp4_errno.h>

#include <stdio.h>
#include <string.h>

static int failures = 0;

#define CHECK(cond, msg)                                                     \
    do {                                                                     \
        if (cond) {                                                          \
            printf("PASS: %s\n", msg);                                       \
        } else {                                                             \
            printf("FAIL: %s\n", msg);                                       \
            failures++;                                                      \
        }                                                                    \
    } while (0)

int main(void)
{
    /* 1. ccp4uc_calc_rcell: orthorhombic cell 50x60x70 with 90/90/90 angles.
     *    Reciprocal cell a* = 1/a = 0.02, b* = 1/b = 1/60 ~ 0.0166667,
     *    c* = 1/c = 1/70 ~ 0.0142857, angles all 90. */
    double cell[6]  = {50.0, 60.0, 70.0, 90.0, 90.0, 90.0};
    double rcell[6] = {0.0, 0.0, 0.0, 0.0, 0.0, 0.0};
    double rvol = ccp4uc_calc_rcell(cell, rcell);

    printf("rcell = %f %f %f %f %f %f, rvol = %f\n",
           rcell[0], rcell[1], rcell[2], rcell[3], rcell[4], rcell[5], rvol);

    CHECK(rcell[0] > 0.019 && rcell[0] < 0.021, "rcell a* ~ 1/50");
    CHECK(rcell[1] > 0.016 && rcell[1] < 0.017, "rcell b* ~ 1/60");
    CHECK(rcell[2] > 0.014 && rcell[2] < 0.015, "rcell c* ~ 1/70");
    CHECK(rcell[3] > 89.9 && rcell[3] < 90.1, "rcell alpha = 90");
    CHECK(rcell[4] > 89.9 && rcell[4] < 90.1, "rcell beta  = 90");
    CHECK(rcell[5] > 89.9 && rcell[5] < 90.1, "rcell gamma = 90");
    /* volume = a*b*c = 210000, reciprocal volume = 1/210000 ~ 4.76e-6 */
    CHECK(rvol > 4.0e-6 && rvol < 5.5e-6, "reciprocal cell volume");

    /* 2. ccp4uc_frac_orth_mat: build orthogonalisation matrices (ncode=1:
     *    x along a, z along c*), volume check. ncode valid range is 1..6. */
    double ro[3][3] = {{0}}, rf[3][3] = {{0}};
    double vol = ccp4uc_frac_orth_mat(cell, 1, ro, rf);
    printf("frac_orth_mat volume = %f\n", vol);
    CHECK(vol > 209000 && vol < 211000, "orthogonalisation matrix volume");
    CHECK(ro[0][0] != 0.0 || ro[1][1] != 0.0, "orthogonalisation matrix populated");

    /* 3. Coordinate conversion: orth -> frac -> orth roundtrip */
    double xo[3] = {25.0, 30.0, 35.0};
    double xf[3] = {0.0, 0.0, 0.0};
    double xo2[3] = {0.0, 0.0, 0.0};
    ccp4uc_orth_to_frac(rf, xo, xf);
    ccp4uc_frac_to_orth(ro, xf, xo2);
    printf("roundtrip: (%f,%f,%f) -> (%f,%f,%f)\n", xo[0], xo[1], xo[2], xo2[0], xo2[1], xo2[2]);
    CHECK(xo2[0] > 24.9 && xo2[0] < 25.1, "roundtrip x");
    CHECK(xo2[1] > 29.9 && xo2[1] < 30.1, "roundtrip y");
    CHECK(xo2[2] > 34.9 && xo2[2] < 35.1, "roundtrip z");

    /* 4. Error-handling API (ccp4_errno.h / ccp4_general.h) */
    int verb = ccp4_liberr_verbosity(-1);
    printf("ccp4_liberr_verbosity(-1) = %d\n", verb);
    CHECK(verb >= 0, "ccp4_liberr_verbosity queryable");

    const char *msg = ccp4_strerror(ccp4_errno);
    printf("ccp4_strerror(ccp4_errno) = '%s'\n", msg ? msg : "()");
    CHECK(msg != NULL && msg[0] != '\0', "ccp4_strerror returns message");

    if (failures == 0) {
        printf("All libccp4 tests passed!\n");
        return 0;
    }
    printf("%d test(s) FAILED\n", failures);
    return 1;
}
