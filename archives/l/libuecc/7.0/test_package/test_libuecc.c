/*
 * libuecc 7 鸿蒙PC消费者测试
 *
 * 用 libuecc v7 公开 API 验证：
 *   1. 默认 base point（Ed25519 生成元）非 identity
 *   2. 1*G == G（标量 1 乘以 base 在 Ed25519 packed 表示下等于 base 自身）
 *   3. L*G == identity（L 是 base point 的阶 = 2^252+27742317777372353535851937790883648493）
 *   4. ecc_25519_gf_sanitize_secret 的清位性质（bit255 set、bit256 清、bottom 3 bits 清）
 *
 * 重要：`ecc_25519_work_t` 的内部表示不唯一（见 ecc.h 注释），不能直接
 * memcmp 两个点结构体；点等价性必须通过 Ed25519 packed 32 字节表示比较。
 *
 * 通过 exit 0 / 非 0 表达断言失败。
 */
#include <stdio.h>
#include <stdint.h>
#include <string.h>

#include <libuecc/ecc.h>

#define FAIL(msg, ...) do { \
    fprintf(stderr, "FAIL: " msg "\n", ##__VA_ARGS__); \
    return 1; \
} while (0)

/* L = 2^252 + 27742317777372353535851937790883648493
   即 Ed25519 base point 的阶，低字节优先（little-endian）。 */
static const uint8_t ed25519_L_le[32] = {
    0xed, 0xd3, 0xf5, 0x5c, 0x1a, 0x63, 0x12, 0x58,
    0xd6, 0x9c, 0xf7, 0xa2, 0xde, 0xf9, 0xde, 0x14,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x10,
};

int main(void) {
    ecc_25519_work_t P, Q;
    ecc_int256_t scalar;
    ecc_int256_t packed_g, packed_one_g;
    uint8_t raw[32];

    /* 断言 1：默认 base point 不是 identity。 */
    if (ecc_25519_is_identity(&ecc_25519_work_default_base)) {
        FAIL("default base point is identity");
    }

    /* 断言 2：scalar = 1，1*G 的 Ed25519 packed 表示 == base 自身 packed 表示。 */
    memset(raw, 0, sizeof(raw));
    raw[0] = 0x01;
    memcpy(scalar.p, raw, 32);
    ecc_25519_scalarmult(&P, &scalar, &ecc_25519_work_default_base);
    ecc_25519_store_packed_ed25519(&packed_one_g, &P);
    ecc_25519_store_packed_ed25519(&packed_g, &ecc_25519_work_default_base);
    if (memcmp(&packed_one_g, &packed_g, 32) != 0) {
        FAIL("1*G packed != G packed");
    }

    /* 断言 3：scalar = L（base 阶），L*G 应等于 identity。 */
    memcpy(scalar.p, ed25519_L_le, 32);
    ecc_25519_scalarmult(&Q, &scalar, &ecc_25519_work_default_base);
    if (!ecc_25519_is_identity(&Q)) {
        FAIL("L*G is not identity");
    }

    /* 断言 4：sanitize_secret 真实语义（src/ec25519_gf.c:242-251）：
         p[0] &= 0xf8   -> 清除 byte[0] 的低 3 位（即整数的 bit0/bit1/bit2）
         p[31] &= 0x7f  -> 清除 byte[31] 的最高位（整数的 bit255）
         p[31] |= 0x40  -> 设置 byte[31] 的次高位（整数的 bit254）
       （ecc.h 注释里写的 "sets the 255th bit / clears the 256th" 与代码不符；
       这里按实际代码行为断言，符合 Curve25519 / Bernstein 经典规范。） */
    ecc_int256_t raw_secret, sanitized;
    memset(raw_secret.p, 0xff, 32);  /* 全 1 输入，确保被 set/clear 看见 */
    ecc_25519_gf_sanitize_secret(&sanitized, &raw_secret);
    if ((sanitized.p[0]  & 0x07u) != 0)    FAIL("bottom 3 bits not cleared after sanitize");
    if ((sanitized.p[31] & 0x80u) != 0)    FAIL("bit255 not cleared after sanitize");
    if ((sanitized.p[31] & 0x40u) == 0)    FAIL("bit254 not set after sanitize");

    printf("test_libuecc: 4/4 assertions passed\n");
    return 0;
}