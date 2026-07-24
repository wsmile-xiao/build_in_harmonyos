#include <gmp.h>
#include <stdio.h>

int main(void) {
    mpz_t value;
    mpz_init_set_ui(value, 21);
    mpz_mul_ui(value, value, 2);

    if (mpz_cmp_ui(value, 42) != 0) {
        mpz_clear(value);
        return 1;
    }

    gmp_printf("GMP result: %Zd\n", value);
    mpz_clear(value);
    return 0;
}
