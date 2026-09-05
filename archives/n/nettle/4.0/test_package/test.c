#include <stdio.h>
#include <string.h>
#include <nettle/sha2.h>
#include <nettle/aes.h>

int main(void) {
    /* SHA256("abc") must equal ba7816bf... */
    struct sha256_ctx ctx;
    uint8_t digest[SHA256_DIGEST_SIZE];
    const uint8_t abc[] = "abc";
    const uint8_t expected_sha256[SHA256_DIGEST_SIZE] = {
        0xba,0x78,0x16,0xbf,0x8f,0x01,0xcf,0xea,
        0x41,0x41,0x40,0xde,0x5d,0xae,0x22,0x23,
        0xb0,0x03,0x61,0xa3,0x96,0x17,0x7a,0x9c,
        0xb4,0x10,0xff,0x61,0xf2,0x00,0x15,0xad
    };
    sha256_init(&ctx);
    sha256_update(&ctx, 3, abc);
    sha256_digest(&ctx, digest);
    if (memcmp(digest, expected_sha256, SHA256_DIGEST_SIZE) != 0) {
        fprintf(stderr, "SHA256 mismatch!\n");
        return 1;
    }

    /* AES-128 encrypt: key=00..0f, plaintext=00,11..ff -> 69c4e0d8... */
    struct aes128_ctx aes_ctx;
    const uint8_t key16[16] = {0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15};
    const uint8_t pt[16]    = {0x00,0x11,0x22,0x33,0x44,0x55,0x66,0x77,
                               0x88,0x99,0xaa,0xbb,0xcc,0xdd,0xee,0xff};
    const uint8_t expected_ct[16] = {0x69,0xc4,0xe0,0xd8,0x6a,0x7b,0x04,0x30,
                                     0xd8,0xcd,0xb7,0x80,0x70,0xb4,0xc5,0x5a};
    uint8_t ct[16];
    aes128_set_encrypt_key(&aes_ctx, key16);
    aes128_encrypt(&aes_ctx, 16, ct, pt);
    if (memcmp(ct, expected_ct, 16) != 0) {
        fprintf(stderr, "AES-128 encrypt mismatch!\n");
        return 1;
    }

    printf("nettle 4.0 test: SHA256 + AES-128 PASS\n");
    return 0;
}
