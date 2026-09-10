/*
 * Consumer test for the mpfrcx/0.6.3 Conan package (OpenHarmony PC).
 *
 * Uses only public headers (mpfrcx.h from the package include dir) and the
 * packaged library, linked via the mpfrcx::mpfrcx CMake target.
 *
 * Coverage:
 *   - complex high precision polynomial arithmetic: add, sub, mul
 *   - precision control (mpcx_init prec, mpcx_get_prec, mpcx_set_prec)
 *   - real/imaginary parts of coefficients and real part polynomial (mpfrcx_real)
 *   - evaluation at a complex point (mpcx_eval)
 *   - exception/boundary input: zero polynomial (deg -1) evaluation and
 *     comparison, and degree-0 (constant) polynomial behaviour
 */
#include <stdio.h>
#include <stdlib.h>

#include "mpfrcx.h"

#define PREC 128

static int failures = 0;

static void check(const char *what, int cond)
{
    if (cond) {
        printf("[ok] %s\n", what);
    } else {
        printf("[FAIL] %s\n", what);
        failures++;
    }
}

/* Compare an mpc coefficient against integer real/imag parts exactly. */
static int mpc_eq_si_si(mpc_srcptr z, long re, long im)
{
    mpfr_t t;
    int ok;
    mpfr_init2(t, PREC);
    mpc_real(t, z, MPC_RNDNN);
    ok = mpfr_cmp_si(t, re) == 0;
    mpc_imag(t, z, MPC_RNDNN);
    ok = ok && (mpfr_cmp_si(t, im) == 0);
    mpfr_clear(t);
    return ok;
}

int main(void)
{
    /* ── Build p1(x) = (1+2i) + (3-4i) x, p2(x) = (5+7i) + (-1+1i) x ── */
    mpcx_t p1, p2, sum, diff, prod;
    mpc_t c;
    mpcx_init(p1, 2, PREC);
    mpcx_init(p2, 2, PREC);
    mpcx_init(sum, 2, PREC);
    mpcx_init(diff, 2, PREC);
    mpcx_init(prod, 4, PREC);
    mpc_init2(c, PREC);

    mpc_set_si_si(c, 1, 2, MPC_RNDNN);
    mpcx_set_deg(p1, 1);
    mpcx_set_coeff(p1, 0, c);
    mpc_set_si_si(c, 3, -4, MPC_RNDNN);
    mpcx_set_coeff(p1, 1, c);

    mpc_set_si_si(c, 5, 7, MPC_RNDNN);
    mpcx_set_deg(p2, 1);
    mpcx_set_coeff(p2, 0, c);
    mpc_set_si_si(c, -1, 1, MPC_RNDNN);
    mpcx_set_coeff(p2, 1, c);

    check("init precision is honoured", mpcx_get_prec(p1) == PREC);

    /* ── addition: (6+9i) + (2-3i) x ── */
    mpcx_add(sum, p1, p2);
    check("add degree", mpcx_get_deg(sum) == 1);
    check("add coeff 0 = 6+9i", mpc_eq_si_si(mpcx_get_coeff(sum, 0), 6, 9));
    check("add coeff 1 = 2-3i", mpc_eq_si_si(mpcx_get_coeff(sum, 1), 2, -3));

    /* ── subtraction: p1 - p2 = (-4-5i) + (4-5i) x ── */
    mpcx_sub(diff, p1, p2);
    check("sub coeff 0 = -4-5i", mpc_eq_si_si(mpcx_get_coeff(diff, 0), -4, -5));
    check("sub coeff 1 = 4-5i", mpc_eq_si_si(mpcx_get_coeff(diff, 1), 4, -5));

    /* ── multiplication: constant and linear terms ──
     * p1*p2 = c0*d0 + (c0*d1 + c1*d0) x + c1*d1 x^2
     * c0*d0 = (1+2i)(5+7i)  = 5+7i+10i-14 = -9+17i
     * c0*d1+c1*d0 = (1+2i)(-1+i)+(3-4i)(5+7i)
     *             = (-1+i-2i+2i^2) + (15+21i-20i-28i^2)
     *             = (-3-i) + (43+i) = 40
     * c1*d1 = (3-4i)(-1+i) = -3+3i+4i-4i^2 = 1+7i
     */
    mpcx_mul(prod, p1, p2);
    check("mul degree", mpcx_get_deg(prod) == 2);
    check("mul coeff 0 = -9+17i", mpc_eq_si_si(mpcx_get_coeff(prod, 0), -9, 17));
    check("mul coeff 1 = 40+0i", mpc_eq_si_si(mpcx_get_coeff(prod, 1), 40, 0));
    check("mul coeff 2 = 1+7i", mpc_eq_si_si(mpcx_get_coeff(prod, 2), 1, 7));

    /* ── precision control: set_prec resets to the zero polynomial
     * (documented upstream semantics, same as mpc_set_prec), so use a
     * scratch polynomial and only check the precision read-back. ── */
    {
        mpcx_t scratch;
        mpcx_init(scratch, 1, PREC);
        mpcx_set_prec(scratch, 256);
        check("set_prec to 256", mpcx_get_prec(scratch) == 256);
        check("set_prec resets to zero", mpcx_get_deg(scratch) == -1);
        mpcx_set_prec(scratch, PREC);
        check("set_prec back to 128", mpcx_get_prec(scratch) == PREC);
        mpcx_clear(scratch);
    }

    /* ── evaluation at x = i: p1(i) = (1+2i) + (3-4i)i = 1+2i+3i+4 = 5+5i ── */
    {
        mpc_t x, r;
        mpc_init2(x, PREC);
        mpc_init2(r, PREC);
        mpc_set_si_si(x, 0, 1, MPC_RNDNN);
        mpcx_eval(r, p1, x);
        check("eval p1(i) = 5+5i", mpc_eq_si_si(r, 5, 5));
        mpc_clear(r);
        mpc_clear(x);
    }

    /* ── real/imaginary part polynomials ──
     * mpfrcx_real(h, f) keeps the real coefficients of f; for p1 that is
     * 1 + 3x. Evaluating at 2 gives 7.
     */
    {
        mpfrx_t re;
        mpfr_t x2, r2;
        mpfrx_init(re, 2, PREC);
        mpfr_init2(x2, PREC);
        mpfr_init2(r2, PREC);
        mpfrcx_real(re, p1);
        check("real part degree", mpfrx_get_deg(re) == 1);
        mpfr_set_si(x2, 2, GMP_RNDN);
        mpfrx_eval(r2, re, x2);
        check("real part eval at 2 = 7", mpfr_cmp_si(r2, 7) == 0);
        mpfr_clear(r2);
        mpfr_clear(x2);
        mpfrx_clear(re);
    }

    /* ── boundary: zero polynomial has degree -1 ── */
    {
        mpcx_t zero, also_zero;
        mpc_t r;
        mpcx_init(zero, 1, PREC);
        mpcx_init(also_zero, 1, PREC);
        mpc_init2(r, PREC);
        /* default-initialised polynomial is the zero polynomial */
        check("zero polynomial degree is -1", mpcx_get_deg(zero) == -1);
        mpcx_add(sum, zero, also_zero);
        check("zero + zero is zero", mpcx_get_deg(sum) == -1);
        mpcx_eval(r, zero, mpcx_get_coeff(p1, 0));
        check("eval of zero polynomial gives 0+0i", mpc_eq_si_si(r, 0, 0));
        check("zero equals zero (mpcx_cmp)", mpcx_cmp(zero, also_zero) == 0);
        mpcx_mul(prod, zero, p2);
        check("zero * p2 is zero", mpcx_get_deg(prod) == -1);
        mpc_clear(r);
        mpcx_clear(also_zero);
        mpcx_clear(zero);
    }

    /* ── boundary: degree-0 constant polynomial ── */
    {
        mpcx_t k;
        mpcx_init(k, 1, PREC);
        mpc_set_si_si(c, -6, 8, MPC_RNDNN);
        mpcx_set_deg(k, 0);
        mpcx_set_coeff(k, 0, c);
        check("constant polynomial degree 0", mpcx_get_deg(k) == 0);
        {
            mpc_t x, r;
            mpc_init2(x, PREC);
            mpc_init2(r, PREC);
            mpc_set_si_si(x, 100, -100, MPC_RNDNN);
            mpcx_eval(r, k, x);
            check("constant eval is constant", mpc_eq_si_si(r, -6, 8));
            mpc_clear(r);
            mpc_clear(x);
        }
        mpcx_clear(k);
    }

    /* ── polynomial comparison ── */
    {
        mpcx_t copy;
        mpcx_init_set(copy, p2);
        check("copy equals original", mpcx_cmp(copy, p2) == 0);
        mpcx_clear(copy);
    }

    mpc_clear(c);
    mpcx_clear(prod);
    mpcx_clear(diff);
    mpcx_clear(sum);
    mpcx_clear(p2);
    mpcx_clear(p1);

    if (failures) {
        printf("test_mpfrcx: %d check(s) FAILED\n", failures);
        return 1;
    }
    printf("test_mpfrcx: all checks passed\n");
    return 0;
}
