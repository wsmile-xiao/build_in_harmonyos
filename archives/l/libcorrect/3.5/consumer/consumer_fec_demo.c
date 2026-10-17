/*
 * 消费者用例 — libcorrect 3.5（模拟业务上层组件）
 *
 * 模拟一个“数据链路 FEC 保护层”：业务应用把一条 64 字节的遥测报文交给
 * FEC 层，FEC 层用 libcorrect 的 Reed-Solomon (255, 223) 公开 API 为报文
 * 追加 32 字节校验码；链路对报文注入 5 处随机位损坏后，业务侧调用同一公开
 * API 解码并恢复原始报文。
 *
 * 仅使用库已安装/导出的公开头文件 <correct.h> 与公开 API：
 *   correct_reed_solomon_create / encode / decode / decode_with_erasures / destroy
 * 调用具有业务意义的可观察结果：恢复后的报文逐字节等于原始报文，
 * 且损坏字节数与恢复后差异均为 0。
 *
 * 与上游 ctest、鸿蒙专项测试（tests-ohos）分别计数。
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <correct.h>

#define PAYLOAD_LEN 223  /* RS(255,223) 数据区 */
#define PARITY_LEN 32    /* 校验区 */
#define BLOCK_LEN (PAYLOAD_LEN + PARITY_LEN)
#define TELEMETRY_LEN 64

/* 业务报文：模拟 64 字节遥测帧 */
typedef struct {
    uint8_t magic[4];
    uint16_t seq;
    uint8_t data[TELEMETRY_LEN];
} __attribute__((packed)) telemetry_frame;

int main(void) {
    correct_reed_solomon *rs = correct_reed_solomon_create(
        correct_rs_primitive_polynomial_8_7_2_1_0, 1, 1, PARITY_LEN);
    if (!rs) {
        fprintf(stderr, "consumer: create RS instance failed\n");
        return 1;
    }

    telemetry_frame frame;
    memset(&frame, 0, sizeof(frame));
    memcpy(frame.magic, "TELM", 4);
    frame.seq = 42;
    for (size_t i = 0; i < TELEMETRY_LEN; i++) {
        frame.data[i] = (uint8_t)(i ^ 0x5A);
    }

    /* 编码：将业务帧复制进 RS(255,223) 数据区（223 字节），
     * 剩余填充 0，再编成带校验的 255 字节码块。不可把 70 字节的
     * packed 帧直接按 223 字节传给 encode（stack-buffer-over-read）。 */
    uint8_t payload[PAYLOAD_LEN];
    memset(payload, 0, sizeof(payload));
    memcpy(payload, &frame, sizeof(frame));

    uint8_t codeword[BLOCK_LEN];
    ssize_t written = correct_reed_solomon_encode(rs, payload, PAYLOAD_LEN, codeword);
    if (written != BLOCK_LEN) {
        fprintf(stderr, "consumer: encode failed (rc=%zd)\n", written);
        correct_reed_solomon_destroy(rs);
        return 1;
    }

    /* 信道：注入 5 处字节损坏 */
    const size_t corrupt_pos[5] = {8, 64, 128, 192, 240};
    const uint8_t corrupt_val[5] = {0x11, 0x22, 0x33, 0x44, 0x55};
    for (int i = 0; i < 5; i++) {
        codeword[corrupt_pos[i]] ^= corrupt_val[i];
    }

    /* 解码恢复 */
    uint8_t recovered[PAYLOAD_LEN];
    ssize_t got = correct_reed_solomon_decode(rs, codeword, BLOCK_LEN, recovered);
    if (got != PAYLOAD_LEN) {
        fprintf(stderr, "consumer: decode failed (rc=%zd)\n", got);
        correct_reed_solomon_destroy(rs);
        return 1;
    }

    telemetry_frame *out = (telemetry_frame *)recovered;
    /* 与 223 字节的 payload 数据区比对（而非 70 字节 frame 越界读） */
    int diffs = memcmp(payload, recovered, PAYLOAD_LEN);
    if (diffs != 0 || memcmp(out->magic, "TELM", 4) != 0 || out->seq != 42) {
        fprintf(stderr, "consumer: payload mismatch after FEC recovery\n");
        correct_reed_solomon_destroy(rs);
        return 1;
    }

    correct_reed_solomon_destroy(rs);
    printf("consumer OK: telemetry frame (seq=%u, %u bytes) survived 5 corrupted "
           "bytes via libcorrect RS(255,223) public API\n",
           (unsigned)out->seq, (unsigned)TELEMETRY_LEN);
    return 0;
}