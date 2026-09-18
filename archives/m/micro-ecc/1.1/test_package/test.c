/* test_package 消费者验证 — micro-ecc 1.1
 * 真实调用 micro-ecc API：对每个启用曲线执行
 *   1) 生成密钥对 uECC_make_key
 *   2) ECDH 共享秘密一致性 uECC_shared_secret（双向比对）
 *   3) ECDSA 签名/验签 uECC_sign / uECC_verify
 * 任一断言失败非零退出。
 */
#include "uECC.h"

#include <stdio.h>
#include <string.h>

static int rng(uint8_t *dest, unsigned size) {
    static uint32_t seed = 0x9E3779B9u;
    for (unsigned i = 0; i < size; ++i) {
        seed = seed * 1664525u + 1013904223u;
        dest[i] = (uint8_t)(seed >> 24);
    }
    return 1;
}

int main(void) {
    const uECC_Curve curves[] = {
        uECC_secp160r1(), uECC_secp192r1(), uECC_secp224r1(),
        uECC_secp256r1(), uECC_secp256k1(),
    };
    const int num_curves = 5;
    int failures = 0;

    uECC_set_rng(&rng);

    for (int c = 0; c < num_curves; ++c) {
        uECC_Curve curve = curves[c];
        int priv_size = uECC_curve_private_key_size(curve);
        int pub_size = uECC_curve_public_key_size(curve);
        uint8_t priv1[32] = {0}, priv2[32] = {0};
        uint8_t pub1[64] = {0}, pub2[64] = {0};
        uint8_t secret1[32] = {0}, secret2[32] = {0};
        uint8_t msg[16] = {1, 2, 3, 4, 5, 6, 7, 8,
                           9, 10, 11, 12, 13, 14, 15, 16};
        uint8_t sig[64] = {0};

        char tag[32];
        snprintf(tag, sizeof(tag), "curve#%d", c);

        if (uECC_make_key(pub1, priv1, curve) != 1 ||
            uECC_make_key(pub2, priv2, curve) != 1) {
            printf("FAIL %s: uECC_make_key\n", tag);
            ++failures;
            continue;
        }
        if (uECC_shared_secret(pub2, priv1, secret1, curve) != 1 ||
            uECC_shared_secret(pub1, priv2, secret2, curve) != 1) {
            printf("FAIL %s: uECC_shared_secret\n", tag);
            ++failures;
            continue;
        }
        if (memcmp(secret1, secret2, (size_t)priv_size) != 0) {
            printf("FAIL %s: shared secrets differ\n", tag);
            ++failures;
            continue;
        }
        if (uECC_sign(priv1, msg, sizeof(msg), sig, curve) != 1) {
            printf("FAIL %s: uECC_sign\n", tag);
            ++failures;
            continue;
        }
        if (uECC_verify(pub1, msg, sizeof(msg), sig, curve) != 1) {
            printf("FAIL %s: uECC_verify\n", tag);
            ++failures;
            continue;
        }
        printf("PASS %s: keygen/ECDH/ECDSA ok (priv=%d pub=%d)\n",
               tag, priv_size, pub_size);
    }

    if (failures != 0) {
        printf("RESULT: %d curve(s) FAILED\n", failures);
        return 1;
    }
    printf("RESULT: all curves passed\n");
    return 0;
}