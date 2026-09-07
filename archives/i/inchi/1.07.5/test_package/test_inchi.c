#include <stdio.h>
#include <string.h>

#include <inchi_api.h>

static int checks_run = 0;

#define CHECK(expression, message)                                            \
    do {                                                                      \
        ++checks_run;                                                         \
        if (!(expression)) {                                                  \
            fprintf(stderr, "check %d failed: %s\n", checks_run, message);   \
            return 1;                                                         \
        }                                                                     \
    } while (0)

int main(void)
{
    static const char water_inchi[] = "InChI=1S/H2O/h1H2";
    static const char water_key[] = "XLYOFNOQVPJJNP-UHFFFAOYSA-N";
    char key[28] = {0};
    char extra_hash_1[65] = {0};
    char extra_hash_2[65] = {0};

    CHECK(CheckINCHI(water_inchi, 0) == INCHI_VALID_STANDARD,
          "standard water InChI must validate");
    CHECK(CheckINCHI("not-an-inchi", 1) == INCHI_INVALID_PREFIX,
          "invalid prefix must be rejected");
    CHECK(GetINCHIKeyFromINCHI(water_inchi, 1, 1, key, extra_hash_1,
                               extra_hash_2) == INCHIKEY_OK,
          "InChIKey generation must succeed");
    CHECK(strcmp(key, water_key) == 0,
          "water InChIKey must match the standard value");
    CHECK(CheckINCHIKey(key) == INCHIKEY_VALID_STANDARD,
          "generated InChIKey must validate");
    CHECK(CheckINCHIKey("bad") == INCHIKEY_INVALID_LENGTH,
          "short InChIKey must be rejected");

    printf("InChI consumer checks: %d/6 passed\n", checks_run);
    return 0;
}
