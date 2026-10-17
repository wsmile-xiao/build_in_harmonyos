/*
 * test_package/test.c — Conan L1 test for libscrypt 1.22.
 *
 * Calls the public libscrypt_scrypt() API with deliberately tiny parameters
 * (N=2, r=1, p=1, 32-byte output) so the test uses ~256 bytes of RAM and
 * completes instantly — no CI OOM, no slow run, no heavy default scrypt.
 *
 * Asserts:
 *   1. libscrypt_scrypt returns 0 (success).
 *   2. The derived key matches the known-answer vector captured natively
 *      (so we are truly linking + exercising the Conan-built libscrypt,
 *      not a host stub): the byte-exact 32-byte hex is embedded below.
 *   3. A second call with identical inputs succeeds (rc2 == 0) and
 *      reproduces the same key (determinism).
 */
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include "libscrypt.h"

/* Known-answer vector, captured on the native toolchain with the same
 * upstream sources: scrypt("password","salt", N=2, r=1, p=1, 32B out). */
static const uint8_t EXPECTED[32] = {
    0x6d, 0x1b, 0xb8, 0x78, 0xee, 0xe9, 0xce, 0x4a,
    0x7b, 0x77, 0xd7, 0xa4, 0x41, 0x03, 0x57, 0x4d,
    0x4c, 0xbf, 0xe3, 0xc1, 0x5a, 0xe3, 0x94, 0x0f,
    0x0f, 0xfe, 0x75, 0xcd, 0x5e, 0x1e, 0x0a, 0xfa,
};

static void print_hex(const char *label, const uint8_t *b, size_t n)
{
    fputs(label, stdout);
    fputc('=', stdout);
    for (size_t i = 0; i < n; i++) printf("%02x", b[i]);
    fputc('\n', stdout);
}

int main(void)
{
    const char *pass = "password";
    const char *salt = "salt";

    /* Zero-initialised so a failed call never reads indeterminate memory.
     * This is defence-in-depth — it does NOT replace the return-value
     * checks below; out/out2 are only read after rc/rc2 == 0 is confirmed. */
    uint8_t out[32] = {0};
    /* N must be a power of two > 1; N=2 is the smallest valid value.
     * Memory ~= 128 * N * r = 256 bytes. */
    int rc = libscrypt_scrypt(
        (const uint8_t *)pass, strlen(pass),
        (const uint8_t *)salt, strlen(salt),
        /*N=*/2, /*r=*/1, /*p=*/1, out, sizeof(out));

    printf("ret=%d\n", rc);

    /* Check the return value BEFORE touching the output buffer: a non-zero
     * rc means libscrypt_scrypt() did not write a valid key, so reading
     * `out` here would read possibly-uninitialised memory. */
    if (rc != 0) {
        printf("FAIL: libscrypt_scrypt returned %d (expected 0)\n", rc);
        return 1;
    }

    print_hex("hex", out, 32);
    if (memcmp(out, EXPECTED, 32) != 0) {
        printf("FAIL: derived key does not match known-answer vector\n");
        return 1;
    }

    /* Determinism: identical inputs must reproduce the same key.
     * The second call's return value is saved and checked before out2 is
     * read, printed, or compared — never read out2 on failure. */
    uint8_t out2[32] = {0};
    int rc2 = libscrypt_scrypt(
        (const uint8_t *)pass, strlen(pass),
        (const uint8_t *)salt, strlen(salt),
        2, 1, 1, out2, sizeof(out2));
    printf("ret2=%d\n", rc2);
    if (rc2 != 0) {
        printf("FAIL: second libscrypt_scrypt returned %d (expected 0)\n", rc2);
        return 1;
    }
    print_hex("hex2", out2, 32);
    if (memcmp(out, out2, 32) != 0) {
        printf("FAIL: non-deterministic output across identical calls\n");
        return 1;
    }

    printf("test libscrypt 1.22: OK (KAT + determinism verified)\n");
    return 0;
}
