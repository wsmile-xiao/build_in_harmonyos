/* Consumer verification for libjose 14.
 *
 * Exercises the real public API end to end (8 checks):
 *  1-2. URL-safe Base64 encode/decode round-trip of "hello".
 *  3.   Generate a symmetric oct JWK (256-bit) via jose_jwk_gen.
 *  4.   The generated key carries kty "oct".
 *  5.   Thumbprint (RFC 7638, S256) of the key is computable.
 *  6.   Generate an HS256 JWK.
 *  7-8. HS256 JWS sign then verify round-trip.
 *
 * Exits 0 only if all 8 checks pass; any failure aborts non-zero so the
 * conan test() gate (and the HMBS_TEST_PACKAGE_RESULT marker) reflects
 * the real outcome.
 */
#include <stdio.h>
#include <string.h>

#include <jansson.h>
#include <jose/b64.h>
#include <jose/jose.h>
#include <jose/jwk.h>
#include <jose/jws.h>

static int g_checks = 0;

#define CHECK(cond, label) \
    do { \
        if (!(cond)) { \
            fprintf(stderr, "CHECK FAILED: %s (line %d)\n", label, __LINE__); \
            return 1; \
        } \
        printf("CHECK PASSED: %s\n", label); \
        g_checks++; \
    } while (0)

int
main(void)
{
    /* 1. Base64 encode "hello" -> "aGVsbG8" (URL-safe, no padding). */
    char enc[16] = {0};
    size_t enclen = jose_b64_enc_buf("hello", 5, enc, sizeof(enc));
    CHECK(enclen == 7 && memcmp(enc, "aGVsbG8", 7) == 0, "b64 encode hello");

    /* 2. Decode back to the original bytes. */
    char dec[16] = {0};
    size_t declen = jose_b64_dec_buf(enc, enclen, dec, sizeof(dec));
    CHECK(declen == 5 && memcmp(dec, "hello", 5) == 0, "b64 decode round-trip");

    /* 3. Generate a 256-bit symmetric key. */
    json_auto_t *jwk = json_pack("{s:s,s:i}", "kty", "oct", "bytes", 32);
    CHECK(jwk != NULL && jose_jwk_gen(NULL, jwk), "jose_jwk_gen oct-256");

    /* 4. The generated key keeps kty "oct". */
    {
        json_t *kty = json_object_get(jwk, "kty");
        CHECK(kty != NULL && json_is_string(kty)
              && strcmp(json_string_value(kty), "oct") == 0, "jwk kty is oct");
    }

    /* 5. RFC 7638 thumbprint is computable. */
    {
        json_auto_t *thp = jose_jwk_thp(NULL, jwk, "S256");
        CHECK(thp != NULL && json_is_string(thp)
              && strlen(json_string_value(thp)) > 0, "jwk thumbprint S256");
    }

    /* 6. Generate an HS256 signing key. */
    json_auto_t *hs = json_pack("{s:s}", "alg", "HS256");
    CHECK(hs != NULL && jose_jwk_gen(NULL, hs), "jose_jwk_gen HS256");

    /* 7. Sign a payload. */
    json_auto_t *jws = json_pack("{s:s}", "payload", "hello-jose");
    CHECK(jws != NULL && jose_jws_sig(NULL, jws, NULL, hs), "jose_jws_sig HS256");

    /* 8. Verify the signature. */
    CHECK(jose_jws_ver(NULL, jws, NULL, hs, false), "jose_jws_ver HS256");

    if (g_checks != 8) {
        fprintf(stderr, "CHECK FAILED: expected 8 checks, ran %d\n", g_checks);
        return 1;
    }
    printf("JOSE_CONSUMER_TEST passed 8/8 checks\n");
    json_decref(jwk);
    return 0;
}
