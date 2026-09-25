#include <stdio.h>
#include <string.h>
#include <SpritzCipher.h>

/* Spritz 论文 RS14（Page 30）官方测试向量：hash('ABC') 256-bit */
static const uint8_t expect_hash_abc[32] = {
    0x02, 0x8f, 0xa2, 0xb4, 0x8b, 0x93, 0x4a, 0x18,
    0x62, 0xb8, 0x69, 0x10, 0x51, 0x3a, 0x47, 0x67,
    0x7c, 0x1c, 0x2d, 0x95, 0xec, 0x3e, 0x75, 0x70,
    0x78, 0x6f, 0x1c, 0x32, 0x8b, 0xbd, 0x4a, 0x47
};

/* Spritz 论文 RS14 测试向量：key='ABC' 流输出前 32 字节 */
static const uint8_t expect_stream_abc[32] = {
    0x10, 0x44, 0xa3, 0x18, 0x11, 0xcf, 0x0e, 0xd3,
    0x4f, 0x54, 0x49, 0x5c, 0x1d, 0x41, 0x4e, 0xb3,
    0xfc, 0x90, 0xdb, 0x63, 0x54, 0x35, 0x3a, 0x8e,
    0x74, 0x91, 0x8f, 0x48, 0xc4, 0x1c, 0xa0, 0x39
};

static int failures = 0;

static void check_hash(void) {
    uint8_t digest[32];
    spritz_hash(digest, sizeof(digest), (const uint8_t *)"ABC", 3);
    if (spritz_compare(digest, expect_hash_abc, 32) == 0) {
        printf("[PASS] spritz_hash('ABC') == RS14 vector\n");
    } else {
        printf("[FAIL] spritz_hash('ABC') mismatch\n");
        failures++;
    }
}

static void check_crypt_roundtrip(void) {
    const uint8_t msg[3] = {'A', 'B', 'C'};
    const uint8_t key[3] = {0x00, 0x01, 0x02};
    uint8_t buf[8], dec[8];
    spritz_ctx ctx;
    spritz_setup(&ctx, key, sizeof(key));
    spritz_crypt(&ctx, msg, sizeof(msg), buf);
    spritz_setup(&ctx, key, sizeof(key));
    spritz_crypt(&ctx, buf, sizeof(msg), dec);
    if (spritz_compare(dec, msg, sizeof(msg)) == 0) {
        printf("[PASS] spritz_crypt encrypt->decrypt roundtrip\n");
    } else {
        printf("[FAIL] crypt roundtrip mismatch\n");
        failures++;
    }
}

static void check_mac(void) {
    const uint8_t msg[3] = {'A', 'B', 'C'};
    const uint8_t key[3] = {0x00, 0x01, 0x02};
    uint8_t mac1[16], mac2[16];
    spritz_mac(mac1, sizeof(mac1), msg, sizeof(msg), key, sizeof(key));
    spritz_mac(mac2, sizeof(mac2), msg, sizeof(msg), key, sizeof(key));
    if (spritz_compare(mac1, mac2, sizeof(mac1)) == 0) {
        printf("[PASS] spritz_mac deterministic output\n");
    } else {
        printf("[FAIL] spritz_mac not deterministic\n");
        failures++;
    }
}

static void check_random(void) {
    uint8_t a[64], b[64];
    spritz_ctx ctx;
    uint8_t seed[16] = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16};
    unsigned int i;
    spritz_setup(&ctx, seed, sizeof(seed));
    for (i = 0; i < sizeof(a); i++) a[i] = spritz_random8(&ctx);
    spritz_setup(&ctx, seed, sizeof(seed));
    for (i = 0; i < sizeof(b); i++) b[i] = spritz_random8(&ctx);
    if (spritz_compare(a, b, sizeof(a)) == 0) {
        printf("[PASS] spritz_random8 deterministic PRNG (seeded)\n");
    } else {
        printf("[FAIL] spritz_random8 not deterministic\n");
        failures++;
    }
}

int main(void) {
    printf("test_package: arduinospritzcipher %s\n", SPRITZ_LIBRARY_VERSION_STRING);
    check_hash();
    check_crypt_roundtrip();
    check_mac();
    check_random();
    if (failures == 0) {
        printf("ALL_PASS\n");
        return 0;
    }
    printf("FAILURES=%d\n", failures);
    return 1;
}
