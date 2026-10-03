/* test_package/test_correct.c — libcorrect/0.0-git20260204 消费者测试
 *
 * 真实调用被测包 API 的回环校验（R34）：
 *   [1] Reed-Solomon (255,223,32) CCSDS 本原多项式：encode → 注入 3 字节
 *       损伤 → decode → 与原始消息逐字节比对（纠错能力 t=16 > 3）
 *   [2] 卷积码 rate 1/2 order 7（0161/0127）：encode_len/encode →
 *       hard-decision decode → 逐字节比对
 * 任一断言失败 → 非零退出；无 skip、无静默通过。
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#include <correct.h>

static int test_rs_roundtrip(void) {
    /* (255, 223) RS code with CCSDS primitive polynomial, 32 roots */
    correct_reed_solomon *rs = correct_reed_solomon_create(
        correct_rs_primitive_polynomial_ccsds, 1 /* first_consecutive_root */,
        1 /* generator_root_gap */, 32 /* num_roots */);
    if (!rs) {
        fprintf(stderr, "FAIL: correct_reed_solomon_create returned NULL\n");
        return 1;
    }

    uint8_t msg[223];
    uint8_t encoded[255];
    uint8_t decoded[223];

    for (size_t i = 0; i < sizeof(msg); i++) {
        msg[i] = (uint8_t)(rand() % 256);
    }

    ssize_t enc_len = correct_reed_solomon_encode(
        rs, msg, sizeof(msg), encoded);
    if (enc_len != (ssize_t)sizeof(encoded)) {
        fprintf(stderr, "FAIL: rs encode returned %zd, expected %zu\n",
                enc_len, sizeof(encoded));
        correct_reed_solomon_destroy(rs);
        return 1;
    }

    /* Corrupt 3 bytes; t = num_roots/2 = 16 correctable */
    encoded[0] ^= 0xFF;
    encoded[100] ^= 0xFF;
    encoded[254] ^= 0xFF;

    ssize_t dec_len = correct_reed_solomon_decode(
        rs, encoded, sizeof(encoded), decoded);
    if (dec_len != (ssize_t)sizeof(msg)) {
        fprintf(stderr, "FAIL: rs decode returned %zd, expected %zu\n",
                dec_len, sizeof(msg));
        correct_reed_solomon_destroy(rs);
        return 1;
    }
    if (memcmp(msg, decoded, sizeof(msg)) != 0) {
        fprintf(stderr, "FAIL: rs decoded payload differs from original\n");
        correct_reed_solomon_destroy(rs);
        return 1;
    }

    correct_reed_solomon_destroy(rs);
    printf("PASS: reed-solomon encode/corrupt/decode roundtrip (255,223,32)\n");
    return 0;
}

static int test_conv_roundtrip(void) {
    /* rate 1/2, order 7 convolutional code (K=7, polys 0161 0127) */
    correct_convolutional *conv = correct_convolutional_create(
        2 /* inv_rate */, 7 /* order */, correct_conv_r12_7_polynomial);
    if (!conv) {
        fprintf(stderr, "FAIL: correct_convolutional_create returned NULL\n");
        return 1;
    }

    uint8_t msg[64];
    for (size_t i = 0; i < sizeof(msg); i++) {
        msg[i] = (uint8_t)(rand() % 256);
    }

    size_t enc_bits = correct_convolutional_encode_len(conv, sizeof(msg));
    size_t enc_bytes = enc_bits / 8 + ((enc_bits % 8) ? 1 : 0);
    uint8_t *encoded = calloc(enc_bytes ? enc_bytes : 1, 1);
    uint8_t *decoded = calloc(sizeof(msg) + 8, 1);
    if (!encoded || !decoded) {
        fprintf(stderr, "FAIL: out of memory\n");
        free(encoded);
        free(decoded);
        correct_convolutional_destroy(conv);
        return 1;
    }

    size_t written_bits = correct_convolutional_encode(
        conv, msg, sizeof(msg), encoded);
    if (written_bits != enc_bits) {
        fprintf(stderr, "FAIL: conv encode returned %zu, expected %zu\n",
                written_bits, enc_bits);
        free(encoded);
        free(decoded);
        correct_convolutional_destroy(conv);
        return 1;
    }

    ssize_t dec_len = correct_convolutional_decode(
        conv, encoded, enc_bits, decoded);
    if (dec_len != (ssize_t)sizeof(msg)) {
        fprintf(stderr, "FAIL: conv decode returned %zd, expected %zu\n",
                dec_len, sizeof(msg));
        free(encoded);
        free(decoded);
        correct_convolutional_destroy(conv);
        return 1;
    }
    if (memcmp(msg, decoded, sizeof(msg)) != 0) {
        fprintf(stderr, "FAIL: conv decoded payload differs from original\n");
        free(encoded);
        free(decoded);
        correct_convolutional_destroy(conv);
        return 1;
    }

    free(encoded);
    free(decoded);
    correct_convolutional_destroy(conv);
    printf("PASS: convolutional encode/decode roundtrip (rate 1/2, order 7)\n");
    return 0;
}

int main(void) {
    srand(20260204);
    int rc = 0;
    rc |= test_rs_roundtrip();
    rc |= test_conv_roundtrip();
    if (rc == 0) {
        printf("test_correct: ALL OK\n");
    }
    return rc;
}
