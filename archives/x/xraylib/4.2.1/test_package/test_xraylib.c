/* test_xraylib.c — consumer test for xraylib 4.2.1 (R34 real API calls).
 *
 * Exercises 7 independent core APIs with upstream reference values
 * (taken from tests/test-*.c): AtomicWeight, ElementDensity, LineEnergy,
 * CS_Total, CS_Photo, FluorYield and EdgeEnergy. Each check prints
 * [PASS]/[FAIL] and any mismatch makes the binary exit non-zero, so a
 * stub implementation cannot fake a pass.
 */
#include <stdio.h>
#include <math.h>
#include <string.h>
#include <xraylib.h>

static int failures = 0;

#define CHECK(cond, name, got, want) do { \
    if (cond) { \
        printf("[PASS] %s: got %f want %f\n", (name), (got), (want)); \
    } else { \
        printf("[FAIL] %s: got %f want %f\n", (name), (got), (want)); \
        ++failures; \
    } \
} while (0)

int main(void) {
    xrl_error *error = NULL;
    double v;

    /* 1. AtomicWeight(Fe-26) == 55.850 (tests/test-atomicweight.c). */
    v = AtomicWeight(26, &error);
    CHECK(error == NULL && fabs(v - 55.850) < 1E-6, "AtomicWeight(26)", v, 55.850);
    xrl_clear_error(&error);

    /* 2. ElementDensity(Sn-50) == 7.31 (tests/test-densities.c). */
    v = ElementDensity(50, &error);
    CHECK(error == NULL && fabs(v - 7.31) < 1E-8, "ElementDensity(50)", v, 7.31);
    xrl_clear_error(&error);

    /* 3. LineEnergy(Fe, KL3) == 6.4039 keV (tests/test-fluor_lines.c). */
    v = LineEnergy(26, KL3_LINE, &error);
    CHECK(error == NULL && fabs(v - 6.4039) < 1E-6, "LineEnergy(26,KL3)", v, 6.4039);
    xrl_clear_error(&error);

    /* 4. CS_Total must be positive and equal CS_Photo+CS_Rayl+CS_Compt. */
    {
        double tot = CS_Total(26, 10.0, &error);
        int ok = (error == NULL && tot > 0.0);
        xrl_clear_error(&error);
        double ph = CS_Photo(26, 10.0, &error);
        xrl_clear_error(&error);
        double ra = CS_Rayl(26, 10.0, &error);
        xrl_clear_error(&error);
        double co = CS_Compt(26, 10.0, &error);
        xrl_clear_error(&error);
        ok = ok && fabs(tot - (ph + ra + co)) / tot < 1E-9;
        CHECK(ok, "CS_Total==Photo+Rayl+Compt(Fe,10keV)", tot, ph + ra + co);
    }

    /* 5. CS_Photo(Fe, 10keV) must be positive (sanity, guards stub). */
    v = CS_Photo(26, 10.0, &error);
    CHECK(error == NULL && v > 0.0, "CS_Photo(26,10keV)>0", v, 1.0);
    xrl_clear_error(&error);

    /* 6. FluorYield(Fe, K_SHELL) in (0,1) (physical range check). */
    v = FluorYield(26, K_SHELL, &error);
    CHECK(error == NULL && v > 0.0 && v < 1.0, "FluorYield(26,K) in (0,1)", v, 0.34);
    xrl_clear_error(&error);

    /* 7. EdgeEnergy(Fe, K_SHELL) ~ 7.112 keV (tests/test-edges.c). */
    v = EdgeEnergy(26, K_SHELL, &error);
    CHECK(error == NULL && fabs(v - 7.112) < 0.05, "EdgeEnergy(26,K)", v, 7.112);
    xrl_clear_error(&error);

    /* Error path: invalid Z must fail (mirrors upstream error tests). */
    v = AtomicWeight(185, &error);
    if (v == 0.0 && error != NULL) {
        printf("[PASS] AtomicWeight(185) correctly reports error\n");
        xrl_clear_error(&error);
    } else {
        printf("[FAIL] AtomicWeight(185) should report error\n");
        ++failures;
        xrl_clear_error(&error);
    }

    if (failures) {
        printf("test_xraylib: %d check(s) FAILED\n", failures);
        return 1;
    }
    printf("test_xraylib: all 7 checks passed\n");
    return 0;
}
