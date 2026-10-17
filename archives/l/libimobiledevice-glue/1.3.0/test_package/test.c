/* test_libimobiledevice_glue.c — L1 test for libimobiledevice-glue SHA-256 API.
 *
 * Computes SHA-256 of "abc" and verifies against the known FIPS 180-2
 * test vector: ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad
 */
#include <libimobiledevice-glue/sha.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    /* FIPS 180-2 test vector for "abc" */
    const char *message = "abc";
    unsigned char digest[SHA256_DIGEST_LENGTH];
    int ret;

    /* Compute SHA-256 */
    ret = sha256((const unsigned char *)message, 3, digest);
    if (ret != 0) {
        fprintf(stderr, "FAIL: sha256 returned %d\n", ret);
        return 1;
    }

    /* Expected: ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad */
    static const unsigned char expected[SHA256_DIGEST_LENGTH] = {
        0xba, 0x78, 0x16, 0xbf, 0x8f, 0x01, 0xcf, 0xea,
        0x41, 0x41, 0x40, 0xde, 0x5d, 0xae, 0x22, 0x23,
        0xb0, 0x03, 0x61, 0xa3, 0x96, 0x17, 0x7a, 0x9c,
        0xb4, 0x10, 0xff, 0x61, 0xf2, 0x00, 0x15, 0xad
    };

    if (memcmp(digest, expected, SHA256_DIGEST_LENGTH) != 0) {
        fprintf(stderr, "FAIL: SHA-256 digest does not match expected value\n");
        fprintf(stderr, "  Got: ");
        for (int i = 0; i < SHA256_DIGEST_LENGTH; i++) {
            fprintf(stderr, "%02x", digest[i]);
        }
        fprintf(stderr, "\n  Expected: ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad\n");
        return 1;
    }

    /* Also test the init/update/final interface */
    sha256_context ctx;
    ret = sha256_init(&ctx);
    if (ret != 0) {
        fprintf(stderr, "FAIL: sha256_init returned %d\n", ret);
        return 1;
    }
    ret = sha256_update(&ctx, (const unsigned char *)message, 3);
    if (ret != 0) {
        fprintf(stderr, "FAIL: sha256_update returned %d\n", ret);
        return 1;
    }
    unsigned char digest2[SHA256_DIGEST_LENGTH];
    ret = sha256_final(&ctx, digest2);
    if (ret != 0) {
        fprintf(stderr, "FAIL: sha256_final returned %d\n", ret);
        return 1;
    }
    if (memcmp(digest2, expected, SHA256_DIGEST_LENGTH) != 0) {
        fprintf(stderr, "FAIL: SHA-256 (init/update/final) digest does not match\n");
        return 1;
    }

    printf("PASS: libimobiledevice-glue SHA-256 test passed\n");
    return 0;
}
