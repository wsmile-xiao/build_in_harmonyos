/* test_package/test_macaroons.c — installed-package consumer for libmacaroons 0.3.0.
 * Uses the real C API: create -> add caveat -> serialize round-trip -> verify.
 * Three explicit checks; any failure exits non-zero with a FAIL line.
 * Signatures verified against upstream releases/0.3.0 macaroons.h:
 *   macaroon_serialize_size_hint(M) -> size_t (no version arg)
 *   macaroon_serialize(M, char*, size_t, err) -> 0/-1 (no version arg)
 *   macaroon_deserialize(NUL-terminated base64, err) -> 2 args
 *   no macaroon_error() helper (err printed as int)
 */
#include <stddef.h>
#include <stdio.h>
#include <string.h>

#include "macaroons.h"

static int check_create(void)
{
    enum macaroon_returncode err = MACAROON_SUCCESS;
    struct macaroon *M = macaroon_create(
        (const unsigned char *)"http://mybank/", strlen("http://mybank/"),
        (const unsigned char *)"test-secret-key-0123456789abcdef",
        strlen("test-secret-key-0123456789abcdef"),
        (const unsigned char *)"test-identifier",
        strlen("test-identifier"), &err);
    if (!M) {
        printf("FAIL: macaroon_create: err=%d\n", (int)err);
        return 1;
    }
    if (macaroon_validate(M) != 0) {
        printf("FAIL: macaroon_validate != 0\n");
        macaroon_destroy(M);
        return 1;
    }
    printf("PASS: create+validate\n");
    macaroon_destroy(M);
    return 0;
}

static int check_roundtrip(void)
{
    enum macaroon_returncode err = MACAROON_SUCCESS;
    struct macaroon *M = macaroon_create(
        (const unsigned char *)"http://mybank/", strlen("http://mybank/"),
        (const unsigned char *)"test-secret-key-0123456789abcdef",
        strlen("test-secret-key-0123456789abcdef"),
        (const unsigned char *)"test-identifier",
        strlen("test-identifier"), &err);
    if (!M) {
        printf("FAIL: create for roundtrip: err=%d\n", (int)err);
        return 1;
    }
    struct macaroon *C = macaroon_add_first_party_caveat(
        M, (const unsigned char *)"account = 3735928559",
        strlen("account = 3735928559"), &err);
    if (!C) {
        printf("FAIL: add_first_party_caveat: err=%d\n", (int)err);
        macaroon_destroy(M);
        return 1;
    }
    size_t need = macaroon_serialize_size_hint(C);
    if (need == 0) {
        printf("FAIL: serialize_size_hint == 0\n");
        macaroon_destroy(M);
        macaroon_destroy(C);
        return 1;
    }
    char buf[8192];
    if (need > sizeof(buf)) {
        printf("FAIL: serialize_size_hint %lu exceeds buffer\n",
               (unsigned long)need);
        macaroon_destroy(M);
        macaroon_destroy(C);
        return 1;
    }
    if (macaroon_serialize(C, buf, sizeof(buf), &err) != 0) {
        printf("FAIL: serialize: err=%d\n", (int)err);
        macaroon_destroy(M);
        macaroon_destroy(C);
        return 1;
    }
    if (buf[0] == '\0') {
        printf("FAIL: serialize produced empty output\n");
        macaroon_destroy(M);
        macaroon_destroy(C);
        return 1;
    }
    struct macaroon *D = macaroon_deserialize(buf, &err);
    if (!D) {
        printf("FAIL: deserialize: err=%d\n", (int)err);
        macaroon_destroy(M);
        macaroon_destroy(C);
        return 1;
    }
    if (macaroon_cmp(C, D) != 0) {
        printf("FAIL: round-trip macaroon_cmp != 0\n");
        macaroon_destroy(M);
        macaroon_destroy(C);
        macaroon_destroy(D);
        return 1;
    }
    printf("PASS: caveat+serialize-roundtrip\n");
    macaroon_destroy(M);
    macaroon_destroy(C);
    macaroon_destroy(D);
    return 0;
}

static int check_verify(void)
{
    enum macaroon_returncode err = MACAROON_SUCCESS;
    const char *secret = "test-secret-key-0123456789abcdef";
    struct macaroon *M = macaroon_create(
        (const unsigned char *)"http://mybank/", strlen("http://mybank/"),
        (const unsigned char *)secret, strlen(secret),
        (const unsigned char *)"test-identifier",
        strlen("test-identifier"), &err);
    if (!M) {
        printf("FAIL: create for verify: err=%d\n", (int)err);
        return 1;
    }
    struct macaroon *C = macaroon_add_first_party_caveat(
        M, (const unsigned char *)"account = 3735928559",
        strlen("account = 3735928559"), &err);
    if (!C) {
        printf("FAIL: caveat for verify: err=%d\n", (int)err);
        macaroon_destroy(M);
        return 1;
    }
    struct macaroon_verifier *V = macaroon_verifier_create();
    if (!V) {
        printf("FAIL: verifier_create\n");
        macaroon_destroy(M);
        macaroon_destroy(C);
        return 1;
    }
    if (macaroon_verifier_satisfy_exact(
            V, (const unsigned char *)"account = 3735928559",
            strlen("account = 3735928559"), &err) != 0) {
        printf("FAIL: satisfy_exact: err=%d\n", (int)err);
        macaroon_destroy(M);
        macaroon_destroy(C);
        macaroon_verifier_destroy(V);
        return 1;
    }
    int rc = macaroon_verify(V, C, (const unsigned char *)secret,
                             strlen(secret), NULL, 0, &err);
    if (rc != 0) {
        printf("FAIL: verify: rc=%d err=%d\n", rc, (int)err);
        macaroon_destroy(M);
        macaroon_destroy(C);
        macaroon_verifier_destroy(V);
        return 1;
    }
    printf("PASS: verifier authorizes caveated macaroon\n");
    macaroon_destroy(M);
    macaroon_destroy(C);
    macaroon_verifier_destroy(V);
    return 0;
}

int main(void)
{
    int failures = 0;
    failures += check_create();
    failures += check_roundtrip();
    failures += check_verify();
    if (failures == 0) {
        printf("ALL TESTS PASSED (3/3)\n");
        return 0;
    }
    printf("FAILURES: %d/3 checks failed\n", failures);
    return 1;
}
