#include <math.h>
#include <mpfr.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    const char *version = mpfr_get_version();
    if (version == NULL || strncmp(version, "4.2.", 4) != 0) {
        return 1;
    }

    mpfr_t value;
    mpfr_init2(value, 128);
    mpfr_set_ui(value, 21, MPFR_RNDN);
    mpfr_mul_ui(value, value, 2, MPFR_RNDN);

    if (mpfr_cmp_ui(value, 42) != 0) {
        mpfr_clear(value);
        return 2;
    }

    double result = mpfr_get_d(value, MPFR_RNDN);
    if (fabs(result - 42.0) > 0.0) {
        mpfr_clear(value);
        return 3;
    }

    printf("MPFR %s result: %.1f\n", version, result);
    mpfr_clear(value);
    mpfr_free_cache();
    return 0;
}
