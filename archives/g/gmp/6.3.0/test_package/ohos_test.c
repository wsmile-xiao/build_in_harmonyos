#include <gmp.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int failures = 0;

static void check(int condition, const char *name)
{
    if (condition) {
        printf("PASS: %s\n", name);
    } else {
        printf("FAIL: %s\n", name);
        ++failures;
    }
}

int main(void)
{
    if (GMP_LIMB_BITS != 64 || GMP_NAIL_BITS != 0)
        return 10;

    mpz_t a, b, product, expected;
    mpz_inits(a, b, product, expected, NULL);
    check(mpz_set_str(a, "123456789012345678901234567890", 10) == 0,
          "parse_30_digit_operand_a");
    check(mpz_set_str(b, "987654321098765432109876543210", 10) == 0,
          "parse_30_digit_operand_b");
    check(mpz_set_str(expected,
                     "121932631137021795226185032733622923332237463801111263526900",
                     10) == 0,
          "parse_expected_product");
    mpz_mul(product, a, b);
    check(mpz_cmp(product, expected) == 0, "exact_60_digit_product");

    char *text = mpz_get_str(NULL, 10, product);
    check(text != NULL && strlen(text) == 60, "decimal_output_length");
    char *expected_text = mpz_get_str(NULL, 10, expected);
    check(text != NULL && expected_text != NULL && strcmp(text, expected_text) == 0,
          "decimal_output_value");
    free(text);
    free(expected_text);

    mpz_t base, exponent, modulus, remainder;
    mpz_inits(base, exponent, modulus, remainder, NULL);
    mpz_set_ui(base, 7);
    mpz_set_ui(exponent, 65537);
    mpz_set_ui(modulus, 1000000007);
    mpz_powm(remainder, base, exponent, modulus);
    check(mpz_cmp_ui(remainder, 95353359UL) == 0, "modular_exponentiation");

    mpz_clears(a, b, product, expected, base, exponent, modulus, remainder, NULL);
    if (failures != 0) {
        fprintf(stderr, "OHOS GMP checks failed: %d\n", failures);
        return 1;
    }
    printf("OHOS GMP checks passed: 7/7\n");
    return 0;
}
