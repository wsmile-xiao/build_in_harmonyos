#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <nettle/aes.h>
#include <nettle/sha2.h>

/* Consumer test for nettle 3.10.2: real crypto API calls with assertions. */
int main(void)
{
    /* 1. SHA256: hash "abc", expect the well-known digest. */
    struct sha256_ctx ctx;
    uint8_t digest[SHA256_DIGEST_SIZE];
    static const uint8_t expect[32] = {
        0xba, 0x78, 0x16, 0xbf, 0x8f, 0x01, 0xcf, 0xea,
        0x41, 0x41, 0x40, 0xde, 0x5d, 0xae, 0x22, 0x23,
        0xb0, 0x03, 0x61, 0xa3, 0x96, 0x17, 0x7a, 0x9c,
        0xb4, 0x10, 0xff, 0x61, 0xf2, 0x00, 0x15, 0xad
    };
    int failures = 0;

    sha256_init(&ctx);
    sha256_update(&ctx, 3, (const uint8_t *)"abc");
    sha256_digest(&ctx, SHA256_DIGEST_SIZE, digest);
    if (memcmp(digest, expect, SHA256_DIGEST_SIZE) != 0) {
        fprintf(stderr, "FAIL: SHA256('abc') mismatch\n");
        failures++;
    } else {
        printf("PASS: SHA256('abc') correct\n");
    }

    /* 2. AES-128: encrypt a 16-byte block, expect the known ciphertext. */
    {
        struct aes128_ctx a;
        uint8_t key[16] = {0x00,0x01,0x02,0x03,0x04,0x05,0x06,0x07,
                           0x08,0x09,0x0a,0x0b,0x0c,0x0d,0x0e,0x0f};
        uint8_t in[16]  = {0x00,0x11,0x22,0x33,0x44,0x55,0x66,0x77,
                           0x88,0x99,0xaa,0xbb,0xcc,0xdd,0xee,0xff};
        uint8_t out[16];
        static const uint8_t expect[16] = {
            0x69,0xc4,0xe0,0xd8,0x6a,0x7b,0x04,0x30,
            0xd8,0xcd,0xb7,0x80,0x70,0xb4,0xc5,0x5a
        };
        aes128_set_encrypt_key(&a, key);
        aes128_encrypt(&a, 16, out, in);
        if (memcmp(out, expect, 16) != 0) {
            fprintf(stderr, "FAIL: AES-128 block encrypt mismatch\n");
            failures++;
        } else {
            printf("PASS: AES-128 block encrypt correct\n");
        }
    }

    if (failures > 0) {
        fprintf(stderr, "nettle consumer test: %d failure(s)\n", failures);
        return 1;
    }
    printf("nettle consumer test: OK\n");
    return 0;
}
