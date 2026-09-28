/* test_package consumer test for libaesgm 2013.1.1
 * R34: must actually call the library API - AES-128 roundtrip. */
#include <stdio.h>
#include <string.h>
#include "aes.h"

int main(void) {
    unsigned char key[16] = {0};
    unsigned char in[16], out[16], dec[16];
    aes_encrypt_ctx ctx_e;
    aes_decrypt_ctx ctx_d;
    int i;
    for (i = 0; i < 16; i++) in[i] = (unsigned char)i;
    if (aes_encrypt_key128(key, &ctx_e) != EXIT_SUCCESS) {
        printf("aes_encrypt_key128 failed\n");
        return 1;
    }
    if (aes_decrypt_key128(key, &ctx_d) != EXIT_SUCCESS) {
        printf("aes_decrypt_key128 failed\n");
        return 1;
    }
    aes_encrypt(in, out, &ctx_e);
    aes_decrypt(out, dec, &ctx_d);
    if (memcmp(in, dec, 16) != 0) {
        printf("AES-128 roundtrip MISMATCH\n");
        return 1;
    }
    printf("libaesgm AES-128 roundtrip: OK\n");
    return 0;
}
