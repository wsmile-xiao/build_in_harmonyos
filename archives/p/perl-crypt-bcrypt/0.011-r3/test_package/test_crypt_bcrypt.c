/*
 * test_crypt_bcrypt.c — Conan L1 test for perl-crypt-bcrypt C library API.
 *
 * Tests the crypt_blowfish C functions exported from Bcrypt.so:
 *   - _crypt_blowfish_rn: hash a password and verify
 *   - _crypt_gensalt_blowfish_rn: generate a salt
 *
 * Exits 0 on success, 1 on failure.
 */
#include <stdio.h>
#include <string.h>
#include "crypt_blowfish.h"

static int chk(const char *name, int ok) {
    if (ok) {
        printf("[PASS] %s\n", name);
        return 0;
    }
    printf("[FAIL] %s\n", name);
    return 1;
}

int main(void) {
    int fail = 0;
    char hash[64] = {0};
    char verify[64] = {0};
    char salt[64] = {0};
    char *result;

    printf("=== Crypt::Bcrypt C library test (OpenHarmony/aarch64) ===\n");

    /* Test 1: Hash a password with a known setting */
    result = _crypt_blowfish_rn("hello", "$2b$12$0123456789abcdefghijkl",
                                hash, sizeof(hash));
    fail += chk("Test 1 (bcrypt hash)",
                result != NULL && strncmp(hash, "$2b$", 4) == 0);
    if (result != NULL)
        printf("  hash = %s\n", hash);

    /* Test 2: Verify correct password (re-hash should match) */
    result = _crypt_blowfish_rn("hello", hash, verify, sizeof(verify));
    fail += chk("Test 2 (verify correct password)",
                result != NULL && strcmp(hash, verify) == 0);

    /* Test 3: Reject wrong password (re-hash should differ) */
    result = _crypt_blowfish_rn("wrong", hash, verify, sizeof(verify));
    fail += chk("Test 3 (reject wrong password)",
                result != NULL && strcmp(hash, verify) != 0);

    /* Test 4: Generate salt with $2b$ prefix and cost 12 */
    result = _crypt_gensalt_blowfish_rn("$2b$", 12,
                                         "0123456789abcdef", 16,
                                         salt, sizeof(salt));
    fail += chk("Test 4 (gensalt)",
                result != NULL && strncmp(salt, "$2b$12$", 7) == 0);
    if (result != NULL)
        printf("  salt = %s\n", salt);

    /* Test 5: Generate salt with $2a$ prefix and cost 6 */
    result = _crypt_gensalt_blowfish_rn("$2a$", 6,
                                         "0123456789abcdef", 16,
                                         salt, sizeof(salt));
    fail += chk("Test 5 (gensalt $2a$ cost 6)",
                result != NULL && strncmp(salt, "$2a$06$", 7) == 0);

    if (fail == 0) {
        printf("\nAll Crypt::Bcrypt C library tests PASSED\n");
        return 0;
    }
    printf("\n%d test(s) FAILED\n", fail);
    return 1;
}
