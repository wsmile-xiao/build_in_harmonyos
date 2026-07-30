/* test_package/test.c — aws-lc 5.4.0 consumer test
 *
 * Verifies that aws-lc libcrypto is properly installed and functional.
 * Uses SHA-256 API to compute a known-answer digest.
 */
#include <stdio.h>
#include <string.h>
#include <openssl/sha.h>
#include <openssl/crypto.h>

int main(void) {
    /* Compute SHA-256 of "abc" — well-known answer */
    const char *msg = "abc";
    unsigned char digest[SHA256_DIGEST_LENGTH];
    unsigned char *result = SHA256((const unsigned char *)msg, strlen(msg), digest);
    if (result == NULL) {
        fprintf(stderr, "FAIL: SHA256 returned NULL\n");
        return 1;
    }

    /* Expected SHA-256("abc") = ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad */
    const unsigned char expected[SHA256_DIGEST_LENGTH] = {
        0xba, 0x78, 0x16, 0xbf, 0x8f, 0x01, 0xcf, 0xea,
        0x41, 0x41, 0x40, 0xde, 0x5d, 0xae, 0x22, 0x23,
        0xb0, 0x03, 0x61, 0xa3, 0x96, 0x17, 0x7a, 0x9c,
        0xb4, 0x10, 0xff, 0x61, 0xf2, 0x00, 0x15, 0xad
    };

    if (memcmp(digest, expected, SHA256_DIGEST_LENGTH) != 0) {
        fprintf(stderr, "FAIL: SHA-256 mismatch\n");
        fprintf(stderr, "  got: ");
        for (int i = 0; i < SHA256_DIGEST_LENGTH; i++)
            fprintf(stderr, "%02x", digest[i]);
        fprintf(stderr, "\n");
        return 1;
    }

    /* Check library version */
    const char *ver = OpenSSL_version(OPENSSL_VERSION);
    if (ver == NULL) {
        fprintf(stderr, "FAIL: OpenSSL_version returned NULL\n");
        return 1;
    }

    printf("PASS: aws-lc SHA-256 known-answer test OK\n");
    printf("  Library: %s\n", ver);
    return 0;
}
