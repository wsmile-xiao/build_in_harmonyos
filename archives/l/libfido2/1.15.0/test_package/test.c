#include <stdio.h>
#include <string.h>

#include <fido.h>
#include <fido/es256.h>
#include <fido/rs256.h>
#include <fido/eddsa.h>
#include <fido/err.h>

/* 实质调用 libfido2 API（R34：禁止空壳测试）
 * - fido_init: 初始化库
 * - fido_dev_new/fido_dev_free: 设备对象生命周期
 * - es256_pk_new/es256_pk_from_ptr/es256_pk_free: ES256 公钥导入
 * - rs256_pk_new/rs256_pk_free, eddsa_pk_new/eddsa_pk_free: 其他算法公钥对象
 * - fido_strerr: 错误码转字符串
 */
int main(void) {
    fido_init(0);

    /* 设备对象 */
    fido_dev_t *dev = fido_dev_new();
    if (dev == NULL) {
        fprintf(stderr, "FAIL: fido_dev_new returned NULL\n");
        return 1;
    }
    fido_dev_free(&dev);
    if (dev != NULL) {
        fprintf(stderr, "FAIL: fido_dev_free did not NULL the pointer\n");
        return 1;
    }

    /* ES256 公钥对象：导入合法 EC 公钥（上游 regress/es256.c p256v1_raw 用例，
     * 65 字节 uncompressed 格式，es256_pk_to_EVP_PKEY 会做 EC_POINT 校验，
     * 任意字节序列会被拒绝） */
    static const unsigned char p256v1_raw[65] = {
        0x04, 0x3b, 0x08, 0xaa, 0xd7, 0x87, 0x3c, 0xd1,
        0xbe, 0xc2, 0xd4, 0x9c, 0xec, 0xc7, 0x9c, 0x35,
        0xcc, 0xcb, 0xe4, 0xd8, 0x68, 0x16, 0xe6, 0x47,
        0xc6, 0x30, 0xe2, 0x97, 0x8f, 0x01, 0x7f, 0x53,
        0xee, 0x75, 0x65, 0xf0, 0x43, 0x29, 0xe8, 0x6c,
        0xde, 0x2b, 0xdd, 0x79, 0x70, 0x09, 0x06, 0x4c,
        0x48, 0x87, 0xb1, 0x37, 0x88, 0x0d, 0xf6, 0xb3,
        0xe1, 0xf2, 0x36, 0xa9, 0x3e, 0x9e, 0xd9, 0x7d,
        0x7e,
    };
    es256_pk_t *pk = es256_pk_new();
    if (pk == NULL) {
        fprintf(stderr, "FAIL: es256_pk_new returned NULL\n");
        return 1;
    }
    /* uncompressed 格式（0x04 前缀）与 libfido2 x||y 格式各测一次（上游 valid_curve 同款） */
    if (es256_pk_from_ptr(pk, p256v1_raw, sizeof(p256v1_raw)) != FIDO_OK) {
        fprintf(stderr, "FAIL: es256_pk_from_ptr(uncompressed)\n");
        return 1;
    }
    if (es256_pk_from_ptr(pk, p256v1_raw + 1, sizeof(p256v1_raw) - 1) != FIDO_OK) {
        fprintf(stderr, "FAIL: es256_pk_from_ptr(x||y)\n");
        return 1;
    }
    es256_pk_free(&pk);

    /* RS256 / EdDSA 公钥对象 */
    rs256_pk_t *rp = rs256_pk_new();
    eddsa_pk_t *ep = eddsa_pk_new();
    if (rp == NULL || ep == NULL) {
        fprintf(stderr, "FAIL: rs256_pk_new/eddsa_pk_new\n");
        return 1;
    }
    rs256_pk_free(&rp);
    eddsa_pk_free(&ep);

    /* 错误字符串（FIDO_OK = 0） */
    const char *s = fido_strerr(FIDO_OK);
    if (s == NULL || s[0] == '\0') {
        fprintf(stderr, "FAIL: fido_strerr(FIDO_OK)\n");
        return 1;
    }

    printf("libfido2 test_package OK: fido_init/fido_dev_new/es256_pk_from_ptr/"
           "rs256_pk/eddsa_pk/fido_strerr all passed\n");
    return 0;
}
