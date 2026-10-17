/**
 *  @brief Consumer smoke test for the NumKong dispatch library on OHOS.
 *
 *  Calls the C API exported by libnumkong.so (nk_capabilities, nk_dot_f32,
 *  nk_euclidean_f64, nk_haversine_f64) and asserts the numeric results
 *  against analytically known values, so a broken dispatch build fails.
 */
#include <math.h>
#include <stdio.h>

#include "numkong/numkong.h"

int main(void) {
    /* Runtime capability probe must report baseline NEON on aarch64. */
    nk_capability_t caps = nk_capabilities();
    if (!(caps & nk_cap_neon_k)) {
        printf("FAIL: expected NEON capability on aarch64 host (caps=0x%llx)\n",
               (unsigned long long)caps);
        return 1;
    }
    printf("capabilities: neon=%d sve=%d (dynamic dispatch: %d)\n",
           (int)!!(caps & nk_cap_neon_k), (int)!!(caps & nk_cap_sve_k),
           nk_uses_dynamic_dispatch());

    /* Dot product: [1,2,3] . [4,5,6] = 32 */
    {
        nk_f32_t a[3] = {1.0f, 2.0f, 3.0f};
        nk_f32_t b[3] = {4.0f, 5.0f, 6.0f};
        nk_f64_t result = 0.0;
        nk_dot_f32(a, b, 3, &result);
        if (fabs(result - 32.0) > 1e-9) {
            printf("FAIL: nk_dot_f32 = %f, expected 32.0\n", result);
            return 2;
        }
        printf("nk_dot_f32([1,2,3],[4,5,6]) = %f\n", result);
    }

    /* Euclidean distance: dist([0,0],[3,4]) = 5 */
    {
        nk_f64_t a[2] = {0.0, 0.0};
        nk_f64_t b[2] = {3.0, 4.0};
        nk_f64_t result = 0.0;
        nk_euclidean_f64(a, b, 2, &result);
        if (fabs(result - 5.0) > 1e-12) {
            printf("FAIL: nk_euclidean_f64 = %f, expected 5.0\n", result);
            return 3;
        }
        printf("nk_euclidean_f64([0,0],[3,4]) = %f\n", result);
    }

    /* Haversine distance between the two poles is half the earth
     * circumference for the default sphere radius: pi * 6335439 m
     * (NK_EARTH_MEDIATORIAL_RADIUS, IERS-2003) = 19903368.62 m.
     * Inputs are radians (see geospatial.h), outputs are meters. */
    {
        nk_f64_t a_lats[1] = {1.5707963267948966};  /* +pi/2 */
        nk_f64_t a_lons[1] = {0.0};
        nk_f64_t b_lats[1] = {-1.5707963267948966}; /* -pi/2 */
        nk_f64_t b_lons[1] = {0.0};
        nk_f64_t result = 0.0;
        nk_haversine_f64(a_lats, a_lons, b_lats, b_lons, 1, &result);
        if (fabs(result - 19903368.62) > 1.0) {
            printf("FAIL: nk_haversine_f64 = %f, expected ~19903368.62 m\n", result);
            return 4;
        }
        printf("nk_haversine_f64(N,S) = %f m\n", result);
    }

    printf("All NumKong consumer checks passed.\n");
    return 0;
}
