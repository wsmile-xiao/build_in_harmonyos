#include <stdio.h>
#include <string.h>

#include "aes.h"
#include "sha256.h"

int main(void) {
    aes_context aes;
    uint8 key[32];
    uint8 plain[16] = "Hello AES Crypt";
    uint8 cipher[16];
    uint8 decrypted[16];

    memset(key, 0x42, sizeof(key));

    /* AES-256 encrypt/decrypt round-trip */
    if (aes_set_key(&aes, key, 256) != 0) {
        fprintf(stderr, "FAIL: aes_set_key failed\n");
        return 1;
    }
    aes_encrypt(&aes, plain, cipher);
    aes_decrypt(&aes, cipher, decrypted);
    if (memcmp(plain, decrypted, 16) != 0) {
        fprintf(stderr, "FAIL: AES encrypt/decrypt round-trip mismatch\n");
        return 1;
    }

    /* SHA-256 hash */
    sha256_context sha;
    uint8 digest[32];
    uint8 expected[32] = {
        0xb8, 0xf0, 0x55, 0x79, 0x92, 0x74, 0x05, 0x4b,
        0x70, 0x2d, 0x35, 0x93, 0xd5, 0x3f, 0x04, 0x32,
        0x52, 0xc1, 0x7e, 0x4b, 0x25, 0x92, 0xf6, 0xcb,
        0xc8, 0x2f, 0xc4, 0x9a, 0x79, 0x95, 0xcc, 0x11
    };
    uint8 message[] = "Hello AES Crypt";
    sha256_starts(&sha);
    sha256_update(&sha, message, 15);
    sha256_finish(&sha, digest);
    if (memcmp(digest, expected, 32) != 0) {
        fprintf(stderr, "FAIL: SHA-256 digest mismatch\n");
        return 1;
    }

    printf("PASS: aescrypt-packetizer smoke test OK\n");
    return 0;
}