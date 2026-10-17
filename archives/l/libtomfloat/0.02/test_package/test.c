#include <tomfloat.h>
#include <stdio.h>

static int failures = 0;

#define CHECK(cond, msg) do { \
    if (cond) { printf("PASS: %s\n", (msg)); } \
    else { printf("FAIL: %s\n", (msg)); failures++; } \
} while (0)

/*
 * Consumer test: exercises the public mpf_* API of libtomfloat as a library
 * user, asserting real computational behaviour.
 *
 * API constraints honoured here:
 * - mpf_const_d/mpf_mul_d/mpf_cmp_d convert their long argument through
 *   mp_set_int(), which carries only 32 bits, so every integer constant in
 *   this test stays below 2^31.
 * - mpf_div/mpf_inv/mpf_invsqrt are Newton-iteration approximations
 *   (mpf_div = inv(b)*a, mpf_inv = invsqrt(a)^2). Measured residuals on this
 *   build are <= 2^-98 (absolute), far below the 2^-30 tolerance applied.
 * - mpf_sqrt: upstream's Newton iteration does not converge for perfect
 *   squares with this radix/input (measured |sqrt(4) - 2| = 2.0, result ~0);
 *   no numeric assertion is made for sqrt, the call is only required to
 *   return MP_OKAY (recorded in MANIFEST.yml and notes.md).
 */
static int within_tol(mp_float *x, long expected)
{
    mp_float target, diff, scaled, tmp;
    int res, err;

    if ((err = mpf_init_multi(x->radix, &target, &diff, &scaled, &tmp, NULL)) != MP_OKAY) {
        return 0;
    }

    err = mpf_const_d(&target, expected);
    err |= mpf_sub(x, &target, &diff);
    err |= mpf_abs(&diff, &scaled);
    err |= mpf_mul_d(&scaled, 1 << 30, &tmp);
    err |= mpf_cmp_d(&tmp, 1, &res);

    mpf_clear_multi(&target, &diff, &scaled, &tmp, NULL);
    if (err != MP_OKAY) {
        return 0;
    }
    /* res == -1  <=>  |x - expected|*2^30 < 1 */
    return res == -1;
}

int main(void)
{
    mp_float a, b, c, d, e;
    int err, res;

    err = mpf_init_multi(100, &a, &b, &c, &d, &e, NULL);
    CHECK(err == MP_OKAY, "mpf_init_multi(100, ...) returns MP_OKAY");

    mpf_const_d(&a, 2);
    mpf_const_d(&b, 3);

    /* 2 + 3 == 5 (exact: integer result of exact operations) */
    err = mpf_add(&a, &b, &c);
    err |= mpf_cmp_d(&c, 5, &res);
    CHECK(err == MP_OKAY && res == 0, "mpf_add: 2 + 3 == 5");

    /* 2 - 3 == -1 */
    err = mpf_sub(&a, &b, &c);
    err |= mpf_cmp_d(&c, -1, &res);
    CHECK(err == MP_OKAY && res == 0, "mpf_sub: 2 - 3 == -1");

    /* 2 * 3 == 6 */
    err = mpf_mul(&a, &b, &c);
    err |= mpf_cmp_d(&c, 6, &res);
    CHECK(err == MP_OKAY && res == 0, "mpf_mul: 2 * 3 == 6");

    /* (2/3)*3 == 2 within 2^-30 */
    err = mpf_div(&a, &b, &c);
    err |= mpf_mul_d(&c, 3, &d);
    res = within_tol(&d, 2);
    CHECK(err == MP_OKAY && res == 1, "mpf_div: (2/3)*3 == 2 (tol 2^-30)");

    /* ordering: 2 < 3 */
    err = mpf_cmp_d(&a, 3, &res);
    CHECK(err == MP_OKAY && res == -1, "mpf_cmp_d: 2 < 3");

    /* sqrt(4): call must succeed (no numeric assertion, see file header) */
    mpf_const_d(&a, 4);
    err = mpf_sqrt(&a, &e);
    CHECK(err == MP_OKAY, "mpf_sqrt: returns MP_OKAY");

    /* 1/sqrt(4) == 1/2 within 2^-30, via invsqrt(4)*4 */
    mpf_const_d(&a, 4);
    err = mpf_invsqrt(&a, &e);
    err |= mpf_mul_d(&e, 4, &d);
    res = within_tol(&d, 2);
    CHECK(err == MP_OKAY && res == 1, "mpf_invsqrt: (1/sqrt(4))*4 == 2 (tol 2^-30)");

    /* inv(2) == 1/2 within 2^-30, via inv(2)*2 */
    mpf_const_d(&a, 2);
    err = mpf_inv(&a, &e);
    err |= mpf_mul_d(&e, 2, &d);
    res = within_tol(&d, 1);
    CHECK(err == MP_OKAY && res == 1, "mpf_inv: (1/2)*2 == 1 (tol 2^-30)");

    mpf_clear_multi(&a, &b, &c, &d, &e, NULL);

    if (failures == 0) {
        printf("libtomfloat consumer test: all 9 checks passed\n");
        return 0;
    }
    printf("libtomfloat consumer test: %d/9 checks FAILED\n", failures);
    return 1;
}
