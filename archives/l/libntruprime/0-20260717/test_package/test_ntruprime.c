/* test_ntruprime.c — libntruprime/0-20260717 consumer test (TAP-style).
 *
 * 消费者视角验证：链接已打包的 libntruprime（含静态捆绑的 randombytes），
 * 对全部 6 个 sntrup 参数集各执行一次 keypair → enc → dec 往返，
 * 并对 sntrup1277 额外验证封装的随机化（两次封装密文不同且均可解封）。
 * 共 8 个检查点，每通过一项打印一行 "ok N - ..."，供 conanfile.py 解析
 * 生成 HMBS_TEST_PACKAGE_RESULT。无需外部服务。
 */

#include <stdio.h>
#include <string.h>

#include <ntruprime.h>

#define CHECK(cond, id, label) do { \
    if (cond) { printf("ok %d - %s\n", (id), (label)); } \
    else { printf("not ok %d - %s\n", (id), (label)); failed = 1; } \
} while (0)

static int failed = 0;

/* 各参数集往返检查：返回 1 表示通过 */
#define ROUNDTRIP(lower, upper, id) do { \
    static unsigned char pk_##lower[upper##_PUBLICKEYBYTES]; \
    static unsigned char sk_##lower[upper##_SECRETKEYBYTES]; \
    static unsigned char ct_##lower[upper##_CIPHERTEXTBYTES]; \
    static unsigned char k1_##lower[upper##_BYTES]; \
    static unsigned char k2_##lower[upper##_BYTES]; \
    upper##_keypair(pk_##lower, sk_##lower); \
    upper##_enc(ct_##lower, k1_##lower, pk_##lower); \
    upper##_dec(k2_##lower, ct_##lower, sk_##lower); \
    CHECK(memcmp(k1_##lower, k2_##lower, upper##_BYTES) == 0, \
          (id), #lower " kem roundtrip"); \
} while (0)

int main(void)
{
    ROUNDTRIP(sntrup653, sntrup653, 1);
    ROUNDTRIP(sntrup761, sntrup761, 2);
    ROUNDTRIP(sntrup857, sntrup857, 3);
    ROUNDTRIP(sntrup953, sntrup953, 4);
    ROUNDTRIP(sntrup1013, sntrup1013, 5);
    ROUNDTRIP(sntrup1277, sntrup1277, 6);

    /* 封装随机化：同一公钥两次封装，密文应不同，且各自均可正确解封 */
    {
        static unsigned char pk[sntrup1277_PUBLICKEYBYTES];
        static unsigned char sk[sntrup1277_SECRETKEYBYTES];
        static unsigned char cta[sntrup1277_CIPHERTEXTBYTES];
        static unsigned char ctb[sntrup1277_CIPHERTEXTBYTES];
        static unsigned char ka[sntrup1277_BYTES];
        static unsigned char kb[sntrup1277_BYTES];
        static unsigned char da[sntrup1277_BYTES];
        static unsigned char db[sntrup1277_BYTES];

        sntrup1277_keypair(pk, sk);
        sntrup1277_enc(cta, ka, pk);
        sntrup1277_enc(ctb, kb, pk);
        sntrup1277_dec(da, cta, sk);
        sntrup1277_dec(db, ctb, sk);
        CHECK(memcmp(cta, ctb, sntrup1277_CIPHERTEXTBYTES) != 0,
              7, "sntrup1277 encapsulation randomized");
        CHECK(memcmp(ka, da, sntrup1277_BYTES) == 0 &&
              memcmp(kb, db, sntrup1277_BYTES) == 0,
              8, "sntrup1277 double encapsulation decapsulates");
    }

    if (failed) {
        printf("consumer test FAILED\n");
        return 1;
    }
    printf("consumer test ok: 8/8 checks passed\n");
    return 0;
}
