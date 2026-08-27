/* test.c — BearSSL consumer test: compute SHA-256 using the BearSSL API */
#include <bearssl.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    /* Compute SHA-256 of "hello" using BearSSL */
    br_sha256_context ctx;
    unsigned char out[32];
    const char *msg = "hello";
    const unsigned char expected[32] = {
        0x2c, 0xf2, 0x4d, 0xba, 0x5f, 0xb0, 0xa3, 0x0e,
        0x26, 0xe8, 0x3b, 0x2a, 0xc5, 0xb9, 0xe2, 0x9e,
        0x1b, 0x16, 0x1e, 0x5c, 0x1f, 0xa7, 0x42, 0x5e,
        0x73, 0x04, 0x33, 0x62, 0x93, 0x8b, 0x98, 0x24
    };

    br_sha256_init(&ctx);
    br_sha256_update(&ctx, msg, 5);
    br_sha256_out(&ctx, out);

    if (memcmp(out, expected, 32) != 0) {
        printf("FAIL: SHA-256 mismatch\n");
        return 1;
    }

    printf("PASS: SHA-256 of 'hello' verified via BearSSL\n");
    return 0;
}
