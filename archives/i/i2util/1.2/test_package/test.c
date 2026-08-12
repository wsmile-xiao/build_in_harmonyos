#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "I2util/sha1.h"

static int check_digest(const char *label, const uint8_t *data, uint32_t len,
                        const char *expect_hex) {
    uint8_t digest[I2SHA1_DIGEST_SIZE];
    char hex[I2SHA1_DIGEST_SIZE * 2 + 1];
    int i;

    I2Sha1(data, len, digest);
    for (i = 0; i < I2SHA1_DIGEST_SIZE; i++) {
        sprintf(hex + i * 2, "%02x", digest[i]);
    }
    hex[I2SHA1_DIGEST_SIZE * 2] = '\0';

    if (strcmp(hex, expect_hex) != 0) {
        fprintf(stderr, "%s: got %s, expected %s\n", label, hex, expect_hex);
        return 1;
    }
    printf("%s: %s\n", label, hex);
    return 0;
}

int main(void) {
    /* Test vectors from the upstream sha1test regression suite. */
    int fails = 0;

    fails += check_digest("sha1(\"abc\")",
                          (const uint8_t *)"abc", 3,
                          "a9993e364706816aba3e25717850c26c9cd0d89d");
    fails += check_digest("sha1(\"abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq\")",
                          (const uint8_t *)"abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq", 56,
                          "84983e441c3bd26ebaae4aa1f95129e5e54670f1");

    if (fails != 0) {
        fprintf(stderr, "i2util API assertions: %d failed\n", fails);
        return 1;
    }
    printf("i2util API assertions: 2 passed\n");
    return 0;
}
