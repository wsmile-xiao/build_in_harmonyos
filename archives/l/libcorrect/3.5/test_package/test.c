/*
 * test_package 消费者验证 — libcorrect 3.5
 *
 * 通过公开头文件 <correct.h> 与公开 API（correct_reed_solomon_*）完成
 * 一次真实的 Reed-Solomon (255, 223) 编解码：
 *   1. 创建 RS(255,223) 实例（CCSDS 本原多项式 0x187）
 *   2. 对 223 字节消息编码生成 32 字节校验（correct_reed_solomon_encode）
 *   3. 人为破坏编码块中的 4 个字节
 *   4. 解码并核对原始消息完整恢复（correct_reed_solomon_decode）
 *
 * 验证业务可观察结果：解码后的消息与原始消息逐字节一致。
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <correct.h>

#define MSG_LEN 223
#define PARITY_LEN 32
#define BLOCK_LEN (MSG_LEN + PARITY_LEN)

int main(void) {
    correct_reed_solomon *rs = correct_reed_solomon_create(
        correct_rs_primitive_polynomial_8_7_2_1_0, 1, 1, PARITY_LEN);
    if (!rs) {
        fprintf(stderr, "correct_reed_solomon_create failed\n");
        return 1;
    }

    uint8_t msg[MSG_LEN];
    uint8_t encoded[BLOCK_LEN];
    uint8_t decoded[MSG_LEN];

    for (size_t i = 0; i < MSG_LEN; i++) {
        msg[i] = (uint8_t)(i * 7 + 3);
    }

    ssize_t written = correct_reed_solomon_encode(rs, msg, MSG_LEN, encoded);
    if (written != BLOCK_LEN) {
        fprintf(stderr, "encode returned %zd, expected %d\n", written, BLOCK_LEN);
        correct_reed_solomon_destroy(rs);
        return 1;
    }

    /* 破坏 4 个字节（错误数 <= num_roots/2 = 16） */
    encoded[10] ^= 0xFF;
    encoded[100] ^= 0x5A;
    encoded[200] ^= 0xA5;
    encoded[250] ^= 0x01;

    ssize_t recovered = correct_reed_solomon_decode(rs, encoded, BLOCK_LEN, decoded);
    if (recovered != MSG_LEN) {
        fprintf(stderr, "decode returned %zd, expected %d\n", recovered, MSG_LEN);
        correct_reed_solomon_destroy(rs);
        return 1;
    }

    if (memcmp(msg, decoded, MSG_LEN) != 0) {
        fprintf(stderr, "decoded payload does not match original message\n");
        correct_reed_solomon_destroy(rs);
        return 1;
    }

    correct_reed_solomon_destroy(rs);
    printf("test_package OK: RS(255,223) encode+4-byte corruption+decode -> payload recovered intact\n");
    return 0;
}
