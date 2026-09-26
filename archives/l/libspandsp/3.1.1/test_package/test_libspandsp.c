/*
 * libspandsp 3.1.1 消费者测试（R34：真断言，非恒真）
 *
 * 模拟业务上层调用 spandsp 公开 API，覆盖三条链路：
 *   1. G.711 ulaw 编码/解码往返（字节级长度 + 幅度容差断言）
 *   2. DTMF 生成（dtmf_tx 状态机产出样本数与能量断言）
 *   3. CRC-16 ITU 计算（对固定模式序列的已知结果断言——与上游
 *      tests/crc_tests.c 同源的正确性锚点）
 * 任一断言失败 → 非零退出。
 */
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <stdlib.h>
#include <math.h>
#include <stdbool.h>

#include <spandsp/telephony.h>
#include <spandsp/logging.h>
#include <spandsp/super_tone_rx.h>
#include <spandsp/g711.h>
#include <spandsp/dtmf.h>
#include <spandsp/crc.h>

#define SAMPLE_COUNT 160  /* 20ms @ 8kHz */

static int failures = 0;

#define CHECK(cond, msg)                                     \
    do {                                                     \
        if (cond) {                                          \
            printf("OK: %s\n", msg);                         \
        } else {                                             \
            fprintf(stderr, "FAIL: %s\n", msg);              \
            failures++;                                      \
        }                                                    \
    } while (0)

int main(void)
{
    /* ---- 1. G.711 ulaw encode -> decode round trip ---- */
    {
        g711_state_t *enc = g711_init(NULL, G711_ULAW);
        g711_state_t *dec = g711_init(NULL, G711_ULAW);
        int16_t pcm[SAMPLE_COUNT];
        uint8_t ulaw[SAMPLE_COUNT];
        int16_t back[SAMPLE_COUNT];
        int i, len;

        CHECK(enc != NULL && dec != NULL, "g711_init states created");
        if (!enc || !dec) return 1;

        /* 1 kHz sine at moderate amplitude, 8 kHz sample rate */
        for (i = 0; i < SAMPLE_COUNT; i++)
            pcm[i] = (int16_t) lrint(8000.0 * sin(2.0 * 3.14159265358979 * 1000.0 * i / 8000.0));

        len = g711_encode(enc, ulaw, pcm, SAMPLE_COUNT);
        CHECK(len == SAMPLE_COUNT, "g711_encode produced full-length output");
        len = g711_decode(dec, back, ulaw, SAMPLE_COUNT);
        CHECK(len == SAMPLE_COUNT, "g711_decode produced full-length output");

        /* ulaw quantization error must stay within +/- 512 for full scale */
        int worst = 0;
        for (i = 0; i < SAMPLE_COUNT; i++) {
            int delta = back[i] - pcm[i];
            if (delta < 0) delta = -delta;
            if (delta > worst) worst = delta;
        }
        CHECK(worst <= 512, "g711 roundtrip within quantization tolerance");
        printf("  (worst delta=%d)\n", worst);

        g711_release(enc);
        g711_release(dec);
    }

    /* ---- 2. DTMF tone generation ---- */
    {
        dtmf_tx_state_t *gen = dtmf_tx_init(NULL, NULL, NULL);
        int16_t tone[2 * SAMPLE_COUNT];
        int len;

        CHECK(gen != NULL, "dtmf_tx_init state created");
        if (!gen) return 1;

        /* queue digit '1' (697Hz + 1209Hz) */
        CHECK(dtmf_tx_put(gen, "1", 1) >= 0, "dtmf_tx_put queued digit '1'");

        len = dtmf_tx(gen, tone, 2 * SAMPLE_COUNT);
        CHECK(len > 0, "dtmf_tx generated samples");
        if (len > 0) {
            double energy = 0.0;
            int i;
            for (i = 0; i < len; i++)
                energy += (double) tone[i] * tone[i];
            energy /= len;
            /* DTMF 律定 -20dBm 量级：8kHz 16bit 下每样本能量应在千位量级 */
            CHECK(energy > 1000.0, "dtmf tone energy above silence threshold");
            printf("  (energy=%.0f, %d samples)\n", energy, len);
        }
        dtmf_tx_release(gen);
    }

    /* ---- 3. CRC-16 ITU correctness anchor（上游 tests/crc_tests.c 同款
     *     交叉验证模式：块计算 vs 逐位计算，初值 0xFFFF） ---- */
    {
        uint8_t data[] = "123456789";
        uint16_t crc_a = crc_itu16_calc(data, 9, 0xFFFF);
        uint16_t crc_b = 0xFFFF;
        int j;
        for (j = 0; j < 9; j++)
            crc_b = crc_itu16_bits(data[j], 8, crc_b);
        CHECK(crc_a == crc_b && crc_a != 0xFFFF && crc_a != 0x0000,
              "crc_itu16_calc matches bit-by-bit crc_itu16_bits (non-trivial)");
        printf("  (crc16=0x%04X)\n", crc_a);

        /* CRC-16/ITU 算法对固定输入的确定性锚点（初值 0xFFFF 下的已知值，
         * 本机实测 = 块/逐位交叉验证一致值） */
        CHECK(crc_a == 0x6F91, "crc_itu16(\"123456789\", init 0xFFFF) == 0x6F91");

        /* CRC-32 自校验链（上游同款：append 后 check 必须通过） */
        uint8_t buf[32];
        memcpy(buf, data, 9);
        int len = crc_itu32_append(buf, 9);
        CHECK(len == 9 + 4 && crc_itu32_check(buf, len),
              "crc_itu32_append + crc_itu32_check roundtrip");
    }

    if (failures) {
        fprintf(stderr, "*** %d CHECK(S) FAILED ***\n", failures);
        return 1;
    }
    printf("ALL CONSUMER TESTS PASSED\n");
    return 0;
}
