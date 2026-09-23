/*
 * test_package consumer test for spandsp 0.0.6
 *
 * 消费者用例：模拟业务上层调用 spandsp 公开 API，验证编译/链接/运行。
 * 1. G.711 ulaw 编码 + 解码往返（g711_init/g711_encode/g711_decode/g711_release）
 * 2. DTMF 生成（dtmf_tx_init/dtmf_tx_put/dtmf_tx/dtmf_tx_release）
 *
 * 用法参考上游 tests/g711_tests.c 与 tests/dtmf_tx_tests.c。
 */
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <stdlib.h>
#include <inttypes.h>

#include <spandsp/telephony.h>
#include <spandsp/logging.h>
#include <spandsp/super_tone_rx.h>
#include <spandsp/g711.h>
#include <spandsp/dtmf.h>

#define SAMPLE_COUNT 160  /* 20ms @ 8kHz */

int main(void)
{
    int errors = 0;
    int len;

    /* ---- G.711 ulaw encode -> decode round trip ---- */
    {
        g711_state_t *enc_state;
        g711_state_t *dec_state;
        int16_t pcm[SAMPLE_COUNT];
        uint8_t g711_data[SAMPLE_COUNT];
        int16_t decoded[SAMPLE_COUNT];
        int i;

        enc_state = g711_init(NULL, G711_ULAW);
        dec_state = g711_init(NULL, G711_ULAW);
        if (enc_state == NULL || dec_state == NULL) {
            fprintf(stderr, "FAIL: g711_init returned NULL\n");
            return 1;
        }
        /* 1 kHz sine at mid-scale (16-bit @8kHz) */
        for (i = 0; i < SAMPLE_COUNT; i++)
            pcm[i] = (int16_t) (10000.0 * 0.6 * 1000.0 * 2.0 * 3.14159265 * i / 8000.0);

        len = g711_encode(enc_state, g711_data, pcm, SAMPLE_COUNT);
        if (len != SAMPLE_COUNT) {
            fprintf(stderr, "FAIL: g711_encode produced %d samples (expect %d)\n", len, SAMPLE_COUNT);
            errors++;
        }
        len = g711_decode(dec_state, decoded, g711_data, SAMPLE_COUNT);
        if (len != SAMPLE_COUNT) {
            fprintf(stderr, "FAIL: g711_decode produced %d samples (expect %d)\n", len, SAMPLE_COUNT);
            errors++;
        }
        /* spot-check: decode of ulaw must be near original within tolerance */
        for (i = 0; i < SAMPLE_COUNT; i += SAMPLE_COUNT - 1) {
            int delta = decoded[i] - pcm[i];
            if (delta < -512 || delta > 512) {
                fprintf(stderr, "FAIL: g711 roundtrip delta %d at %d out of tolerance\n", delta, i);
                errors++;
            }
        }
        g711_release(enc_state);
        g711_release(dec_state);
        printf("consumer test: G.711 roundtrip OK (%d samples)\n", SAMPLE_COUNT);
    }

    /* ---- DTMF tone generation ---- */
    {
        dtmf_tx_state_t *gen;
        int16_t tone[SAMPLE_COUNT];

        gen = dtmf_tx_init(NULL);
        if (gen == NULL) {
            fprintf(stderr, "FAIL: dtmf_tx_init returned NULL\n");
            return 1;
        }
        if (dtmf_tx_put(gen, "1", -1) < 0) {
            fprintf(stderr, "FAIL: dtmf_tx_put\n");
            errors++;
        }
        len = dtmf_tx(gen, tone, SAMPLE_COUNT);
        if (len != SAMPLE_COUNT) {
            fprintf(stderr, "FAIL: dtmf_tx produced %d samples (expect %d)\n", len, SAMPLE_COUNT);
            errors++;
        }
        dtmf_tx_release(gen);
        printf("consumer test: DTMF generation OK (%d samples)\n", SAMPLE_COUNT);
    }

    if (errors == 0) {
        printf("test_package spandsp 0.0.6 consumer test: OK\n");
        return 0;
    }
    fprintf(stderr, "test_package spandsp 0.0.6 consumer test: %d error(s)\n", errors);
    return 1;
}
