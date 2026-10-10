/*
 * OHOS 专项测试 — libcorrect 3.5
 *
 * 通过公开头文件 <correct.h> 与公开 API 验证 libcorrect 在 HarmonyOS PC
 * (aarch64, OHOS clang) 平台上的完整功能与可观察结果（与上游 ctest 测试、
 * test_package 消费者用例分别计数）。
 *
 * 验证点：
 *   1. 卷积码 (convolutional) payload 往返：编码 → 制造软/硬比特错误 → 解码恢复
 *   2. Reed-Solomon (255, 223) payload 往返：编码 → 破坏字节 → 解码逐字节恢复
 *   3. RS 擦除 (erasure) 路径：显式传擦除位置并用擦除解码接口恢复
 *   4. 返回值/边界语义核对（编码长度、解码长度、破坏超限返回 -1）
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <correct.h>

#define RS_MSG_LEN 223
#define RS_PARITY 32
#define RS_BLOCK_LEN (RS_MSG_LEN + RS_PARITY)

static int ohos_check(int cond, const char *what) {
    if (!cond) {
        fprintf(stderr, "OHOS test FAILED: %s\n", what);
        return 1;
    }
    return 0;
}

/* 卷积码往返：rate 1/2, order 7 (poly {0161, 0127})，msg 8 字节 (64 bit) */
static int test_convolutional_roundtrip(void) {
    const size_t order = 7;
    const size_t inv_rate = 2;
    correct_convolutional_polynomial_t poly[] = {0161, 0127};
    correct_convolutional *conv =
        correct_convolutional_create(inv_rate, order, poly);
    int rc = 0;
    if (ohos_check(conv != NULL, "convolutional create")) {
        return 1;
    }

    uint8_t msg[] = {0xde, 0xad, 0xbe, 0xef, 0x12, 0x34, 0x56, 0x78};
    size_t msg_len = sizeof(msg);             /* 字节单位（API 内部乘 8） */
    size_t msg_bits = msg_len * 8;
    /* encode_len(msg_bytes) = rate * (8*msg_bytes + order + 1) */
    size_t encoded_bits = correct_convolutional_encode_len(conv, msg_len);
    if (ohos_check(encoded_bits == inv_rate * (msg_bits + order + 1), "conv encode_len")) {
        rc = 1;
        goto out;
    }

    size_t enc_bytes = (encoded_bits + 7) / 8;
    uint8_t *encoded = calloc(enc_bytes, 1);
    uint8_t *decoded = calloc(sizeof(msg), 1);
    if (!encoded || !decoded) {
        rc = 1;
        goto out_free;
    }

    size_t written_bits = correct_convolutional_encode(conv, msg, msg_len, encoded);
    if (ohos_check(written_bits == encoded_bits, "conv encode")) {
        rc = 1;
        goto out_free;
    }

    /* 翻转 3 个比特位，模拟信道噪声（Viterbi 可纠正） */
    encoded[0] ^= 0x80;
    encoded[enc_bytes / 2] ^= 0x04;
    encoded[enc_bytes - 1] ^= 0x20;

    ssize_t decoded_bits = correct_convolutional_decode(conv, encoded, encoded_bits, decoded);
    /* decode 返回写入 msg 的字节数（头文件语义） */
    if (ohos_check(decoded_bits == (ssize_t)msg_len, "conv decode len")) {
        rc = 1;
        goto out_free;
    }
    if (ohos_check(memcmp(msg, decoded, sizeof(msg)) == 0, "conv payload recovered")) {
        rc = 1;
        goto out_free;
    }
    printf("OHOS conv roundtrip: rate 1/2 order 7, 3 bit flips recovered, payload intact\n");

out_free:
    free(encoded);
    free(decoded);
out:
    correct_convolutional_destroy(conv);
    return rc;
}

/* RS(255,223) 往返 + 破坏恢复 */
static int test_reed_solomon_roundtrip(void) {
    correct_reed_solomon *rs = correct_reed_solomon_create(
        correct_rs_primitive_polynomial_8_7_2_1_0, 1, 1, RS_PARITY);
    int rc = 0;
    if (ohos_check(rs != NULL, "rs create")) {
        return 1;
    }
    uint8_t msg[RS_MSG_LEN];
    uint8_t encoded[RS_BLOCK_LEN];
    uint8_t decoded[RS_MSG_LEN];
    for (int i = 0; i < RS_MSG_LEN; i++) {
        msg[i] = (uint8_t)(i * 31 + 7);
    }
    ssize_t written = correct_reed_solomon_encode(rs, msg, RS_MSG_LEN, encoded);
    if (ohos_check(written == RS_BLOCK_LEN, "rs encode len")) {
        rc = 1;
        goto out;
    }
    encoded[5] ^= 0xFF;
    encoded[77] ^= 0x3C;
    encoded[150] ^= 0xC3;
    encoded[222] ^= 0xFF;
    ssize_t rec = correct_reed_solomon_decode(rs, encoded, RS_BLOCK_LEN, decoded);
    if (ohos_check(rec == RS_MSG_LEN, "rs decode len")) {
        rc = 1;
        goto out;
    }
    if (ohos_check(memcmp(msg, decoded, RS_MSG_LEN) == 0, "rs payload recovered")) {
        rc = 1;
        goto out;
    }
    printf("OHOS rs roundtrip: RS(255,223), 4 corrupted bytes recovered, payload intact\n");
out:
    correct_reed_solomon_destroy(rs);
    return rc;
}

/* RS 擦除路径 + 超限破坏返回 -1 语义 */
static int test_reed_solomon_erasure_and_overcorrupt(void) {
    correct_reed_solomon *rs = correct_reed_solomon_create(
        correct_rs_primitive_polynomial_8_7_2_1_0, 1, 1, RS_PARITY);
    int rc = 0;
    if (ohos_check(rs != NULL, "rs create (2nd)")) {
        return 1;
    }
    uint8_t msg[RS_MSG_LEN];
    uint8_t encoded[RS_BLOCK_LEN];
    uint8_t decoded[RS_MSG_LEN];
    for (int i = 0; i < RS_MSG_LEN; i++) {
        msg[i] = (uint8_t)(i + 1);
    }
    ssize_t written_er = correct_reed_solomon_encode(rs, msg, RS_MSG_LEN, encoded);
    if (ohos_check(written_er == RS_BLOCK_LEN, "rs erasure encode len")) {
        rc = 1;
        goto out;
    }

    /* 8 个擦除位置，无附加错误：2*0 + 8 < 32 可恢复 */
    uint8_t erased[8] = {3, 50, 100, 120, 180, 200, 240, 254};
    for (int i = 0; i < 8; i++) {
        encoded[erased[i]] = 0x00;
    }
    ssize_t rec = correct_reed_solomon_decode_with_erasures(
        rs, encoded, RS_BLOCK_LEN, erased, 8, decoded);
    if (ohos_check(rec == RS_MSG_LEN, "rs erasure decode len")) {
        rc = 1;
        goto out;
    }
    if (ohos_check(memcmp(msg, decoded, RS_MSG_LEN) == 0, "rs erasure payload recovered")) {
        rc = 1;
        goto out;
    }
    printf("OHOS rs erasure: 8 explicit erasures recovered, payload intact\n");

    /* 超限破坏（>= num_roots 字节）：decode 必须返回 -1 或无法恢复（允许但不要求 -1,
     * 上游语义: 过于损坏时返回 -1；这里验证接口不崩溃且极端情形不误报成功无依据——
     * 只验证调用路径可运行）。 */
    uint8_t msg2[RS_MSG_LEN];
    uint8_t encoded2[RS_BLOCK_LEN];
    uint8_t decoded2[RS_MSG_LEN];
    for (int i = 0; i < RS_MSG_LEN; i++) {
        msg2[i] = (uint8_t)(i * 3 + 1);
    }
    ssize_t written_oc = correct_reed_solomon_encode(rs, msg2, RS_MSG_LEN, encoded2);
    if (ohos_check(written_oc == RS_BLOCK_LEN, "rs overcorrupt encode len")) {
        rc = 1;
        goto out;
    }
    for (int i = 0; i < RS_BLOCK_LEN; i += 2) {
        encoded2[i] ^= 0xFF; /* 128 个字节全部损坏，远超 16 可纠上限 */
    }
    ssize_t over = correct_reed_solomon_decode(rs, encoded2, RS_BLOCK_LEN, decoded2);
    if (ohos_check(over <= 0, "over-corrupted decode must not claim recovery")) {
        rc = 1;
        goto out;
    }
    printf("OHOS rs overcorrupt: decode returned %zd as expected (no false recovery)\n", over);
out:
    correct_reed_solomon_destroy(rs);
    return rc;
}

int main(void) {
    int rc = 0;
    rc |= test_convolutional_roundtrip();
    rc |= test_reed_solomon_roundtrip();
    rc |= test_reed_solomon_erasure_and_overcorrupt();
    if (rc == 0) {
        printf("OHOS 专项测试全部通过 (3/3)\n");
    }
    return rc;
}