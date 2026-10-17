/*
 * Consumer test for ascon-c 1.3.0 (HarmonyOS PC).
 *
 * Uses only the installed public headers (crypto_aead.h / crypto_hash.h /
 * api.h from the asconv13 combined reference implementation) and the
 * exported public API (crypto_aead_encrypt / crypto_aead_decrypt /
 * crypto_hash).  Verifies:
 *   1. AEAD round-trip: encrypt then decrypt returns the original plaintext
 *      and a valid tag (ascon128, 16-byte key/nonce/tag).
 *   2. AEAD tamper detection: flipping a ciphertext byte fails decryption.
 *   3. Hash: crypto_hash() output matches the NIST LWC known-answer vector
 *      for the empty message (LWC_HASH_KAT_256.txt first entry).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "crypto_aead.h"
#include "crypto_hash.h"
#include "api.h"

/* 256-bit hash of the empty message, from the official upstream
 * LWC_HASH_KAT_256.txt (Count = 1, MD = 0B3BE5850F2F6B98...04D92B2). */
static const unsigned char empty_hash[CRYPTO_BYTES] = {
    0x0b, 0x3b, 0xe5, 0x85, 0x0f, 0x2f, 0x6b, 0x98,
    0xca, 0xf2, 0x9f, 0x8f, 0xde, 0xa8, 0x9b, 0x64,
    0xa1, 0xfa, 0x70, 0xaa, 0x24, 0x9b, 0x8f, 0x83,
    0x9b, 0xd5, 0x3b, 0xaa, 0x30, 0x4d, 0x92, 0xb2,
};

int main(void) {
    unsigned char k[CRYPTO_KEYBYTES];
    unsigned char npub[CRYPTO_NPUBBYTES];
    unsigned char m[64];
    unsigned char c[64 + CRYPTO_ABYTES];
    unsigned char m2[64];
    unsigned char h[CRYPTO_BYTES];
    unsigned long long clen = 0;
    unsigned long long mlen2 = 0;
    size_t i;
    int failures = 0;

    /* deterministic test inputs */
    for (i = 0; i < sizeof(k); i++) k[i] = (unsigned char)i;
    for (i = 0; i < sizeof(npub); i++) npub[i] = (unsigned char)(0x80 + i);
    for (i = 0; i < sizeof(m); i++) m[i] = (unsigned char)(i * 7);

    /* 1. AEAD round-trip */
    if (crypto_aead_encrypt(c, &clen, m, sizeof(m), NULL, 0, NULL, npub, k) != 0) {
        printf("FAIL: crypto_aead_encrypt returned non-zero\n");
        failures++;
    } else if (clen != sizeof(m) + CRYPTO_ABYTES) {
        printf("FAIL: ciphertext length %llu != %zu\n", clen, sizeof(m) + CRYPTO_ABYTES);
        failures++;
    } else if (crypto_aead_decrypt(m2, &mlen2, NULL, c, clen, NULL, 0, npub, k) != 0) {
        printf("FAIL: crypto_aead_decrypt rejected valid ciphertext\n");
        failures++;
    } else if (mlen2 != sizeof(m) || memcmp(m, m2, sizeof(m)) != 0) {
        printf("FAIL: decrypted plaintext differs from original\n");
        failures++;
    } else {
        printf("OK: AEAD round-trip (ascon128, %zu-byte message, tag verified)\n", sizeof(m));
    }

    /* 2. Tamper detection */
    if (clen > 0) {
        c[clen / 2] ^= 0x01; /* flip one ciphertext byte */
        if (crypto_aead_decrypt(m2, &mlen2, NULL, c, clen, NULL, 0, npub, k) == 0) {
            printf("FAIL: tampered ciphertext was accepted\n");
            failures++;
        } else {
            printf("OK: tampered ciphertext rejected (integrity check works)\n");
        }
    }

    /* 3. Hash known-answer vector */
    if (crypto_hash(h, NULL, 0) != 0) {
        printf("FAIL: crypto_hash returned non-zero\n");
        failures++;
    } else if (memcmp(h, empty_hash, CRYPTO_BYTES) != 0) {
        printf("FAIL: hash of empty message differs from LWC KAT\n");
        failures++;
    } else {
        printf("OK: crypto_hash matches LWC known-answer vector\n");
    }

    if (failures == 0) {
        printf("ALL TESTS PASSED\n");
        return 0;
    }
    printf("FAILURES: %d\n", failures);
    return 1;
}
