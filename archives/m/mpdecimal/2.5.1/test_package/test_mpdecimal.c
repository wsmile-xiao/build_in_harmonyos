/*
 * test_mpdecimal.c — smoke test for libmpdec (mpdecimal 2.5.1).
 *
 * Exercises the core decimal arithmetic APIs: context setup, mpd_qadd,
 * mpd_qmul, mpd_qdiv, mpd_qabs, mpd_qsqrt, string conversion and
 * error/status handling.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <mpdecimal.h>

static int failures = 0;

static void check_str(const char *label, mpd_t *res, const char *expected) {
    char *s = mpd_to_sci(res, 0);
    if (s == NULL || strcmp(s, expected) != 0) {
        fprintf(stderr, "FAIL %s: got '%s', expected '%s'\n", label,
                s ? s : "()", expected);
        failures++;
    } else {
        printf("PASS %s = %s\n", label, s);
    }
    mpd_free(s);
}

int main(void) {
    mpd_context_t ctx;
    mpd_t *a, *b, *res;
    uint32_t status = 0;
    char *s;

    /* 28-digit precision context (mpd_init sets prec and sane emax/emin) */
    mpd_init(&ctx, 28);

    /* Version sanity */
    s = strdup(mpd_version());
    if (strncmp(s, "2.5.1", 5) != 0) {
        fprintf(stderr, "FAIL version: got '%s', expected '2.5.1'\n", s);
        failures++;
    } else {
        printf("PASS version = %s\n", s);
    }
    free(s);

    /* Addition: 12345678901234567890 + 98765432109876543210 */
    a = mpd_qnew();
    b = mpd_qnew();
    res = mpd_qnew();
    mpd_set_string(a, "12345678901234567890", &ctx);
    mpd_set_string(b, "98765432109876543210", &ctx);
    mpd_qadd(res, a, b, &ctx, &status);
    check_str("qadd", res, "111111111011111111100");

    /* Multiplication: 123456789 * 987654321 = 121932631112635269 */
    mpd_set_string(a, "123456789", &ctx);
    mpd_set_string(b, "987654321", &ctx);
    mpd_qmul(res, a, b, &ctx, &status);
    check_str("qmul", res, "121932631112635269");

    /* Division: 1 / 3 at 28-digit precision */
    mpd_set_string(a, "1", &ctx);
    mpd_set_string(b, "3", &ctx);
    mpd_qdiv(res, a, b, &ctx, &status);
    check_str("qdiv", res, "0.3333333333333333333333333333");

    /* Exact decimal arithmetic: 0.1 + 0.2 == 0.3 (binary FP fails) */
    mpd_set_string(a, "0.1", &ctx);
    mpd_set_string(b, "0.2", &ctx);
    mpd_qadd(res, a, b, &ctx, &status);
    check_str("decimal qadd", res, "0.3");

    /* Absolute value: |-42.5| = 42.5 */
    mpd_set_string(a, "-42.5", &ctx);
    mpd_qabs(res, a, &ctx, &status);
    check_str("qabs", res, "42.5");

    /* Square root: sqrt(2) with max precision context */
    mpd_set_string(a, "2", &ctx);
    mpd_qsqrt(res, a, &ctx, &status);
    check_str("qsqrt", res, "1.414213562373095048801688724");

    /* Status/error handling: division by zero sets MPD_Division_by_zero */
    {
        mpd_t *zero = mpd_qnew();
        mpd_t *num = mpd_qnew();
        mpd_t *out = mpd_qnew();
        uint32_t dstatus = 0;

        mpd_set_string(zero, "0", &ctx);
        mpd_set_string(num, "42", &ctx);
        mpd_qdiv(out, num, zero, &ctx, &dstatus);
        if (dstatus & MPD_Division_by_zero) {
            printf("PASS division-by-zero status raised\n");
        } else {
            fprintf(stderr, "FAIL division-by-zero status not raised\n");
            failures++;
        }
        mpd_del(zero);
        mpd_del(num);
        mpd_del(out);
    }

    mpd_del(a);
    mpd_del(b);
    mpd_del(res);

    if (failures) {
        fprintf(stderr, "test_mpdecimal: %d failure(s)\n", failures);
        return 1;
    }
    printf("test_mpdecimal: all checks passed\n");
    return 0;
}
