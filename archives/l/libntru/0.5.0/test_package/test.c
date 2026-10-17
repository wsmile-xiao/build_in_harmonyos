/* libntru/0.5.0 consumer link + API smoke test.
 *
 * 消费者视角验证：链接 libntru 并执行一次完整的 NTRUEncrypt
 * 密钥生成 → 加密 → 解密往返，无需外部服务。
 */

#include <stdio.h>
#include <string.h>
#include <stdint.h>

#include <ntru.h>
#include <key.h>
#include <rand.h>
#include <encparams.h>

int main(void) {
    const NtruEncParams *params = &EES443EP1;
    NtruRandGen prng = NTRU_RNG_CTR_DRBG;
    NtruRandContext rand_ctx;
    NtruEncKeyPair kp;
    uint8_t seed[32];
    uint8_t plain[24];
    uint16_t plain_len = 24;
    uint8_t enc[1200];
    uint8_t dec[1200];
    uint16_t dec_len;
    int i;

    for (i = 0; i < 32; i++)
        seed[i] = (uint8_t)(0x3C ^ (i * 5));
    if (ntru_rand_init_det(&rand_ctx, &prng, seed, sizeof(seed)) != 0) {
        fprintf(stderr, "rand init failed\n");
        return 1;
    }
    if (ntru_gen_key_pair(params, &kp, &rand_ctx) != 0) {
        fprintf(stderr, "keygen failed\n");
        return 2;
    }
    for (i = 0; i < 24; i++)
        plain[i] = (uint8_t)i;
    if (ntru_encrypt(plain, plain_len, &kp.pub, params, &rand_ctx, enc) != 0) {
        fprintf(stderr, "encrypt failed\n");
        return 3;
    }
    if (ntru_decrypt(enc, &kp, params, dec, &dec_len) != 0) {
        fprintf(stderr, "decrypt failed\n");
        return 4;
    }
    if (dec_len != plain_len || memcmp(dec, plain, plain_len) != 0) {
        fprintf(stderr, "roundtrip mismatch\n");
        return 5;
    }
    printf("libntru api smoke ok\n");
    return 0;
}
