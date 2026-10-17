/* test_tomsfastmath.c — Substantive consumer test for tomsfastmath 0.13.1
 * (Conan L1). Verifies a downstream consumer can link the packaged tfm
 * library and use the bignum API: initialization, add, mul, subtraction,
 * comparison and decimal output, through real assertions. */
#include <tfm.h>
#include <stdio.h>
#include <string.h>

static int failures = 0;
static void check(int cond, const char *label)
{
    if (!cond) { printf("FAIL: %s\n", label); ++failures; }
}

int main(void)
{
    fp_int a, b, c;
    char buf[512];

    /* 1) init and bit count */
    fp_set(&a, 12345);
    check(fp_count_bits(&a) == 14, "fp_count_bits(12345)==14");

    /* 2) add: 12345 + 67890 = 80235 */
    fp_set(&b, 67890);
    fp_add(&a, &b, &c);
    check(fp_cmp_d(&c, 80235) == FP_EQ, "12345+67890==80235");

    /* 3) mul: 111111 * 111111 = 12345654321 */
    fp_set(&a, 111111);
    fp_mul(&a, &a, &c);
    fp_set(&b, 12345654321U);
    check(fp_cmp(&c, &b) == FP_EQ, "111111^2==12345654321");

    /* 4) signed sub: 5 - 10 = -5 */
    fp_set(&a, 5);
    fp_set(&b, 10);
    fp_sub(&a, &b, &c);
    check(c.sign == FP_NEG, "5-10 is negative");
    fp_set(&a, 5);
    fp_sub(&b, &a, &c);
    check(fp_cmp_d(&c, 5) == FP_EQ && c.sign == FP_ZPOS, "10-5==5 positive");

    /* 5) decimal output */
    fp_set(&a, 12345654321U);
    fp_toradix(&a, buf, 10);
    check(strcmp(buf, "12345654321") == 0, "fp_toradix decimal string");

    /* 6) big square: (2^80)^2 has 160 bits */
    fp_set(&a, 1);
    { int i; for (i = 0; i < 80; ++i) fp_mul_2(&a, &a); }
    fp_sqr(&a, &c);
    check(fp_count_bits(&c) == 161, "(2^80)^2 has 161 bits");

    if (failures == 0) {
        printf("PASS: tomsfastmath 0.13.1 library link and bignum API verified\n");
        return 0;
    }
    return 1;
}
