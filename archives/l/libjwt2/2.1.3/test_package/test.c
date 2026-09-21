/* test.c — libjwt2 2.1.3 consumer test (C)
 * 2 real assertions against libjwt v2 API:
 *  1) HS256 encode produces a 3-part token (non-empty, contains '.')
 *  2) decode + grant round-trip returns the original "sub" value.
 */
#include <stdio.h>
#include <string.h>
#include <jwt.h>

static int test_encode(void) {
    jwt_t *jwt = NULL;
    char *token = NULL;
    int ret = 0;

    if (jwt_new(&jwt) != 0 || jwt == NULL) {
        printf("FAIL encode: jwt_new failed\n");
        return 1;
    }
    if (jwt_add_grant(jwt, "sub", "conan-test") != 0) {
        printf("FAIL encode: jwt_add_grant failed\n");
        jwt_free(jwt);
        return 1;
    }
    if (jwt_set_alg(jwt, JWT_ALG_HS256, (const unsigned char *)"secret", 6) != 0) {
        printf("FAIL encode: jwt_set_alg failed\n");
        jwt_free(jwt);
        return 1;
    }
    token = jwt_encode_str(jwt);
    if (token == NULL || token[0] == '\0' || strchr(token, '.') == NULL) {
        printf("FAIL encode: empty or malformed token\n");
        jwt_free(jwt);
        return 1;
    }
    printf("PASS encode: HS256 token len=%lu\n", (unsigned long)strlen(token));
    /* stash token for decode test via static buffer */
    ret = 0;
    jwt_free(jwt);
    /* jwt_encode_str uses internal buffer; re-encode in decode test */
    (void)token;
    return ret;
}

static int test_decode(void) {
    jwt_t *jwt = NULL;
    jwt_t *decoded = NULL;
    char *token = NULL;
    const char *sub = NULL;

    if (jwt_new(&jwt) != 0) {
        printf("FAIL decode: jwt_new failed\n");
        return 1;
    }
    jwt_add_grant(jwt, "sub", "conan-test");
    jwt_set_alg(jwt, JWT_ALG_HS256, (const unsigned char *)"secret", 6);
    token = jwt_encode_str(jwt);
    if (token == NULL) {
        printf("FAIL decode: encode failed\n");
        jwt_free(jwt);
        return 1;
    }
    /* copy token: jwt_encode_str buffer is reused */
    char buf[4096];
    snprintf(buf, sizeof(buf), "%s", token);
    jwt_free(jwt);

    if (jwt_decode(&decoded, buf, (const unsigned char *)"secret", 6) != 0 || decoded == NULL) {
        printf("FAIL decode: jwt_decode failed\n");
        return 1;
    }
    sub = jwt_get_grant(decoded, "sub");
    if (sub == NULL || strcmp(sub, "conan-test") != 0) {
        printf("FAIL decode: sub mismatch: %s\n", sub ? sub : "(null)");
        jwt_free(decoded);
        return 1;
    }
    printf("PASS decode: sub=%s\n", sub);
    jwt_free(decoded);
    return 0;
}

int main(void) {
    int failures = 0;
    failures += test_encode();
    failures += test_decode();
    if (failures != 0) {
        printf("FAIL: %d assertion(s) failed\n", failures);
        return 1;
    }
    printf("test libjwt2 2.1.3: 2/2 consumer assertions OK\n");
    return 0;
}
