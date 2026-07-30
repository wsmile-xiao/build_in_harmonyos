#include <crypt.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int failures;

static void
require_true(int condition, const char *message)
{
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        failures++;
    }
}

int
main(void)
{
    static const char phrase[] = "OpenHarmony libxcrypt consumer";
    static const unsigned char entropy[32] = {
        0x00, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77,
        0x88, 0x99, 0xaa, 0xbb, 0xcc, 0xdd, 0xee, 0xff,
        0x10, 0x21, 0x32, 0x43, 0x54, 0x65, 0x76, 0x87,
        0x98, 0xa9, 0xba, 0xcb, 0xdc, 0xed, 0xfe, 0x0f,
    };
    char setting[CRYPT_GENSALT_OUTPUT_SIZE];
    char saved_hash[CRYPT_OUTPUT_SIZE];
    struct crypt_data data;
    struct crypt_data rn_data;
    void *ra_data = NULL;
    int ra_size = 0;

    const char *method = crypt_preferred_method();
    require_true(method != NULL && method[0] != '\0',
                 "crypt_preferred_method returns a method prefix");
    if (method == NULL || method[0] == '\0') {
        return EXIT_FAILURE;
    }

    char *generated = crypt_gensalt_rn(
        method,
        0,
        (const char *)entropy,
        (int)sizeof(entropy),
        setting,
        (int)sizeof(setting));
    require_true(generated == setting, "crypt_gensalt_rn uses the caller buffer");
    if (generated != setting) {
        return EXIT_FAILURE;
    }
    require_true(strncmp(setting, method, strlen(method)) == 0,
                 "generated setting uses the preferred method");
    require_true(crypt_checksalt(setting) == CRYPT_SALT_OK,
                 "crypt_checksalt accepts the generated setting");

    memset(&data, 0, sizeof(data));
    char *hash = crypt_r(phrase, setting, &data);
    require_true(hash == data.output, "crypt_r uses struct crypt_data output");
    require_true(hash != NULL && hash[0] != '*', "crypt_r creates a valid hash");
    if (hash == NULL || hash[0] == '*') {
        return EXIT_FAILURE;
    }
    require_true(strncmp(hash, method, strlen(method)) == 0,
                 "crypt_r hash uses the preferred method");
    snprintf(saved_hash, sizeof(saved_hash), "%s", hash);

    char *legacy = crypt("wrong phrase", saved_hash);
    require_true(legacy != NULL && strcmp(legacy, saved_hash) != 0,
                 "crypt rejects a different phrase");

    memset(&rn_data, 0, sizeof(rn_data));
    char *rn_hash = crypt_rn(phrase, saved_hash, &rn_data, (int)sizeof(rn_data));
    require_true(rn_hash != NULL, "crypt_rn succeeds with a full crypt_data buffer");
    require_true(rn_hash != NULL && strcmp(rn_hash, saved_hash) == 0,
                 "crypt_rn verifies the stored hash");

    char *ra_hash = crypt_ra(phrase, saved_hash, &ra_data, &ra_size);
    require_true(ra_hash != NULL && ra_size >= (int)sizeof(struct crypt_data),
                 "crypt_ra allocates a sufficiently large buffer");
    require_true(ra_hash != NULL && strcmp(ra_hash, saved_hash) == 0,
                 "crypt_ra verifies the stored hash");
    free(ra_data);

    if (failures == 0) {
        printf("libxcrypt %s consumer API test: PASS\n", XCRYPT_VERSION_STR);
    }
    return failures == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
