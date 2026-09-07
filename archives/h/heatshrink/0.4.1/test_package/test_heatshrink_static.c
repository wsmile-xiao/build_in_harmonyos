/* heatshrink 0.4.1 consumer test — static-allocation flavor.
 *
 * Real consumer of the packaged heatshrink library, linked against the
 * heatshrink::static component (HEATSHRINK_DYNAMIC_ALLOC=0 arrives via the
 * component define). Uses the zero-allocation embedded API: the encoder and
 * decoder are statically allocated and driven with reset/sink/poll/finish.
 *
 * Output: one "PASS <name>" or "FAIL <name>" line per case, then a final
 * "SUMMARY total=<n> pass=<n> fail=<n>" line. Exit code is 0 only when
 * every case passes.
 */

#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "heatshrink_common.h"
#include "heatshrink_decoder.h"
#include "heatshrink_encoder.h"

/* Statically allocated state machines — no malloc/free anywhere. */
static heatshrink_encoder g_hse;
static heatshrink_decoder g_hsd;

static int g_total = 0;
static int g_pass = 0;

#define EXPECT(cond)                                                    \
    do {                                                                \
        if (!(cond)) {                                                  \
            printf("\n    assert failed %s:%d: %s\n", __FILE__, __LINE__, #cond); \
            return -1;                                                  \
        }                                                               \
    } while (0)

/* The static configuration is fixed at compile time by heatshrink_config.h:
 * 8 window bits, 4 lookahead bits, 32-byte decoder input buffer. */
#if !HEATSHRINK_DYNAMIC_ALLOC
#define WINDOW_SZ2 HEATSHRINK_STATIC_WINDOW_BITS
#define LOOKAHEAD_SZ2 HEATSHRINK_STATIC_LOOKAHEAD_BITS
#endif

/* Encode input_size bytes. Returns compressed size or -1. */
static long hs_encode(uint8_t *input, size_t input_size,
                      uint8_t *comp, size_t comp_cap) {
    size_t sunk = 0, polled = 0, count = 0;
    uint8_t poll_buf[128];

    heatshrink_encoder_reset(&g_hse);
    while (sunk < input_size) {
        EXPECT(heatshrink_encoder_sink(&g_hse, &input[sunk], input_size - sunk,
                                       &count) == HSER_SINK_OK);
        EXPECT(count > 0);
        sunk += count;
        for (;;) {
            HSE_poll_res pr = heatshrink_encoder_poll(
                &g_hse, poll_buf, sizeof(poll_buf), &count);
            EXPECT(pr == HSER_POLL_EMPTY || pr == HSER_POLL_MORE);
            EXPECT(polled + count <= comp_cap);
            memcpy(&comp[polled], poll_buf, count);
            polled += count;
            if (pr == HSER_POLL_EMPTY) { break; }
        }
    }
    for (;;) {
        HSE_finish_res fr = heatshrink_encoder_finish(&g_hse);
        EXPECT(fr == HSER_FINISH_DONE || fr == HSER_FINISH_MORE);
        if (fr == HSER_FINISH_DONE) { break; }
        for (;;) {
            HSE_poll_res pr = heatshrink_encoder_poll(
                &g_hse, poll_buf, sizeof(poll_buf), &count);
            EXPECT(pr == HSER_POLL_EMPTY || pr == HSER_POLL_MORE);
            EXPECT(polled + count <= comp_cap);
            memcpy(&comp[polled], poll_buf, count);
            polled += count;
            if (pr == HSER_POLL_EMPTY) { break; }
        }
    }
    return (long)polled;
}

/* Decode comp_sz bytes. Returns decompressed size or -1. */
static long hs_decode(uint8_t *comp, size_t comp_sz,
                      uint8_t *out, size_t out_cap) {
    size_t sunk = 0, polled = 0, count = 0;
    uint8_t poll_buf[128];

    heatshrink_decoder_reset(&g_hsd);
    while (sunk < comp_sz) {
        HSD_sink_res sr = heatshrink_decoder_sink(
            &g_hsd, &comp[sunk], comp_sz - sunk, &count);
        EXPECT(sr == HSDR_SINK_OK || sr == HSDR_SINK_FULL);
        EXPECT(count > 0);
        sunk += count;
        for (;;) {
            HSD_poll_res pr = heatshrink_decoder_poll(
                &g_hsd, poll_buf, sizeof(poll_buf), &count);
            EXPECT(pr == HSDR_POLL_EMPTY || pr == HSDR_POLL_MORE);
            EXPECT(polled + count <= out_cap);
            memcpy(&out[polled], poll_buf, count);
            polled += count;
            if (pr == HSDR_POLL_EMPTY) { break; }
        }
    }
    for (;;) {
        HSD_finish_res fr = heatshrink_decoder_finish(&g_hsd);
        EXPECT(fr == HSDR_FINISH_DONE || fr == HSDR_FINISH_MORE);
        for (;;) {
            HSD_poll_res pr = heatshrink_decoder_poll(
                &g_hsd, poll_buf, sizeof(poll_buf), &count);
            EXPECT(pr == HSDR_POLL_EMPTY || pr == HSDR_POLL_MORE);
            EXPECT(polled + count <= out_cap);
            memcpy(&out[polled], poll_buf, count);
            polled += count;
            if (pr == HSDR_POLL_EMPTY) { break; }
        }
        if (fr == HSDR_FINISH_DONE) { break; }
    }
    return (long)polled;
}

static int roundtrip_case(uint8_t *input, size_t input_size) {
    size_t comp_cap = input_size + input_size / 2 + 64;
    size_t out_cap = input_size + 64;
    uint8_t comp[8192];
    uint8_t out[8192];
    EXPECT(comp_cap <= sizeof(comp));
    EXPECT(out_cap <= sizeof(out));
    memset(comp, 0, sizeof(comp));
    memset(out, 0, sizeof(out));

    long comp_sz = hs_encode(input, input_size, comp, comp_cap);
    EXPECT(comp_sz > 0);
    long out_sz = hs_decode(comp, (size_t)comp_sz, out, out_cap);
    EXPECT(out_sz == (long)input_size);
    EXPECT(memcmp(input, out, input_size) == 0);
    return 0;
}

static int case_config_header(void) {
    /* The static build must be compiled with dynamic allocation off. */
    EXPECT(HEATSHRINK_DYNAMIC_ALLOC == 0);
    EXPECT(HEATSHRINK_STATIC_WINDOW_BITS == 8);
    EXPECT(HEATSHRINK_STATIC_LOOKAHEAD_BITS == 4);
    EXPECT(HEATSHRINK_STATIC_INPUT_BUFFER_SIZE == 32);
    EXPECT(HEATSHRINK_VERSION_MAJOR == 0);
    EXPECT(HEATSHRINK_VERSION_MINOR == 4);
    EXPECT(HEATSHRINK_VERSION_PATCH == 1);
    return 0;
}

static int case_roundtrip_repeated_text(void) {
    const char *chunk = "static alloc works. ";
    uint8_t input[20 * 128];
    for (size_t i = 0; i < sizeof(input); i++) {
        input[i] = (uint8_t)chunk[i % strlen(chunk)];
    }
    EXPECT(roundtrip_case(input, sizeof(input)) == 0);
    return 0;
}

static int case_roundtrip_binary_and_small(void) {
    uint8_t input[2560];
    for (size_t i = 0; i < sizeof(input); i++) {
        input[i] = (uint8_t)((i * 7 + 13) & 0xFF);
    }
    EXPECT(roundtrip_case(input, sizeof(input)) == 0);
    /* Small payload through the tiny fixed input buffer. */
    uint8_t tiny[100];
    memcpy(tiny, "OHOS heatshrink static", 22);
    for (size_t i = 22; i < sizeof(tiny); i++) { tiny[i] = (uint8_t)i; }
    EXPECT(roundtrip_case(tiny, sizeof(tiny)) == 0);
    return 0;
}

int main(void) {
    printf("heatshrink %u.%u.%u consumer test (static allocation)\n",
           HEATSHRINK_VERSION_MAJOR, HEATSHRINK_VERSION_MINOR,
           HEATSHRINK_VERSION_PATCH);

    struct {
        const char *name;
        int (*fn)(void);
    } cases[] = {
        {"config_header", case_config_header},
        {"roundtrip_repeated_text", case_roundtrip_repeated_text},
        {"roundtrip_binary_and_small", case_roundtrip_binary_and_small},
    };

    for (size_t i = 0; i < sizeof(cases) / sizeof(cases[0]); i++) {
        g_total++;
        int rc = cases[i].fn();
        if (rc == 0) {
            g_pass++;
            printf("PASS %s\n", cases[i].name);
        } else {
            printf("FAIL %s\n", cases[i].name);
        }
    }

    printf("SUMMARY total=%d pass=%d fail=%d\n", g_total, g_pass,
           g_total - g_pass);
    return g_pass == g_total ? 0 : 1;
}
