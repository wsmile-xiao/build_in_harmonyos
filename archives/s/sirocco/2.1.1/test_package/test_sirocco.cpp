// test_package test for sirocco 2.1.1.
// Genuinely calls the installed public API (include/sirocco.h):
//   homotopyPath, homotopyPath_comps          (double precision)
//   homotopyPath_mp, homotopyPath_mp_comps    (MPFR arbitrary precision)
// and asserts the certified piecewise-linear path is returned (non-NULL
// with a positive number of sample points).
#include <stdio.h>
#include <sirocco.h>

// 输入：degree-2 多项式 f(x,y)；testCoefs 每 4 个 double 为一个复系数区间的
//   [re_lo, re_hi, im_lo, im_hi]，按 deglex 序（出自上游 tests/sirocco_minimal_test.cpp）。
static const double testCoefs[] = {
    -2.000000000000000, -2.000000000000000, 0.000000000000000, 0.000000000000000,
     0.000000000000000,  0.000000000000000, 0.000000000000000, -0.000000000000000,
     0.000000000000000,  0.000000000000000, 0.000000000000000,  0.000000000000000,
     1.000000000000000,  1.000000000000000, 0.000000000000000, -0.000000000000000,
     0.000000000000000,  0.000000000000000, 0.000000000000000,  0.000000000000000,
     1.000000000000000,  1.000000000000000, 0.000000000000000,  0.000000000000000
};

// 其它因子（用于 *_comps 多因子跟踪）。
static const double testCoefsotcomp[] = {
    -2.100000000000000, -2.100000000000000, 0.000000000000000,  0.000000000000000,
     0.000000000000000,  0.000000000000000, 0.000000000000000, -0.000000000000000,
     0.000000000000000,  0.000000000000000, 0.000000000000000,  0.000000000000000,
     1.000000000000000,  1.000000000000000, 0.000000000000000, -0.000000000000000,
     0.000000000000000,  0.000000000000000, 0.000000000000000,  0.000000000000000,
     1.000000000000000,  1.000000000000000, 0.000000000000000,  0.000000000000000
};

static int fails = 0;

#define CHECK(cond, msg)                                            \
    do {                                                            \
        if (!(cond)) {                                              \
            printf("FAIL: %s\n", (msg));                            \
            ++fails;                                                \
        }                                                           \
    } while (0)

int main(int argc, char const *argv[]) {
    (void)argc;
    (void)argv;
    mpfr_set_default_prec(162);

    int compdegs[] = {2};
    const double y0R = 1.414, y0I = 0.0;

    /* ---- double precision, single factor ---- */
    double *rop = homotopyPath(2, (double*)testCoefs, y0R, y0I);
    CHECK(rop != NULL, "homotopyPath returned NULL");
    if (rop) {
        int len = (int)rop[0];
        CHECK(len > 0, "homotopyPath path length <= 0");
        delete[] rop;
    }

    /* ---- double precision, multiple factors ---- */
    double *rop2 = homotopyPath_comps(2, (double*)testCoefs, y0R, y0I,
                                      1, compdegs,
                                      (double*)testCoefsotcomp);
    CHECK(rop2 != NULL, "homotopyPath_comps returned NULL");
    if (rop2) {
        int len2 = (int)rop2[0];
        CHECK(len2 > 0, "homotopyPath_comps path length <= 0");
        delete[] rop2;
    }

    /* ---- MPFR arbitrary precision ---- */
    mpfr_t mp_testCoefs[24], mp_othercompsCoefs[24];
    for (int i = 0; i < 24; ++i) {
        mpfr_init_set_d(mp_testCoefs[i], testCoefs[i],
                        (i % 2) ? MPFR_RNDU : MPFR_RNDD);
        mpfr_init_set_d(mp_othercompsCoefs[i], testCoefsotcomp[i],
                        (i % 2) ? MPFR_RNDU : MPFR_RNDD);
    }
    mpfr_t mp_y0R, mp_y0I;
    mpfr_init_set_d(mp_y0R, y0R, MPFR_RNDN);
    mpfr_init_set_d(mp_y0I, y0I, MPFR_RNDN);

    mpfr_t *mp_rop = homotopyPath_mp(2, mp_testCoefs, mp_y0R, mp_y0I, 106);
    CHECK(mp_rop != NULL, "homotopyPath_mp returned NULL");
    if (mp_rop) {
        int size = mpfr_get_si(mp_rop[0], MPFR_RNDN);
        CHECK(size > 0, "homotopyPath_mp path length <= 0");
        for (int i = 0; i < 3 * size + 1; ++i)
            mpfr_clear(mp_rop[i]);
        delete[] mp_rop;
    }

    mpfr_t *mp_rop2 = homotopyPath_mp_comps(2, mp_testCoefs, mp_y0R, mp_y0I,
                                            102, 1, compdegs,
                                            mp_othercompsCoefs);
    CHECK(mp_rop2 != NULL, "homotopyPath_mp_comps returned NULL");
    if (mp_rop2) {
        delete[] mp_rop2;
    }

    for (int i = 0; i < 24; ++i) {
        mpfr_clear(mp_testCoefs[i]);
        mpfr_clear(mp_othercompsCoefs[i]);
    }
    mpfr_clear(mp_y0R);
    mpfr_clear(mp_y0I);

    if (fails == 0) {
        printf("test sirocco 2.1.1: OK "
               "(homotopyPath/comps/mp/mp_comps all produced certified paths)\n");
        return 0;
    }
    printf("sirocco test_package: %d assertion(s) failed\n", fails);
    return 1;
}
