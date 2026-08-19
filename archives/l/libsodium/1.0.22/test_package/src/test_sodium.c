// R34: 实质调用 libsodium API — 初始化 + secretbox 加解密
#include <sodium.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    /* sodium_init：初始化 libsodium 库（核心 API） */
    if (sodium_init() < 0) {
        fprintf(stderr, "FAIL: sodium_init 失败\n");
        return 1;
    }
    /* secretbox 加解密往返验证（核心加密 API——非空壳） */
    unsigned char key[crypto_secretbox_KEYBYTES];
    unsigned char nonce[crypto_secretbox_NONCEBYTES];
    randombytes_buf(key, sizeof key);
    randombytes_buf(nonce, sizeof nonce);
    const char *msg = "libsodium test";
    size_t mlen = strlen(msg) + 1;
    unsigned char ciphertext[crypto_secretbox_MACBYTES + 64];
    unsigned char decrypted[64];
    crypto_secretbox_easy(ciphertext, (const unsigned char *)msg, mlen,
                          nonce, key);
    unsigned long long clen = crypto_secretbox_MACBYTES + mlen;
    if (crypto_secretbox_open_easy(decrypted, ciphertext, clen, nonce, key) != 0) {
        fprintf(stderr, "FAIL: crypto_secretbox_open_easy 失败\n");
        return 1;
    }
    if (memcmp(decrypted, msg, mlen) != 0) {
        fprintf(stderr, "FAIL: 解密结果不匹配\n");
        return 1;
    }
    printf("PASS: libsodium API 调用成功（secretbox 加解密往返）\n");
    return 0;
}
