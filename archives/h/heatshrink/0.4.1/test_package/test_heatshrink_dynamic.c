/* heatshrink 0.4.1 consumer test — dynamic-allocation flavor.
 *
 * Real consumer of the packaged heatshrink library, linked against the
 * heatshrink::dynamic component (HEATSHRINK_DYNAMIC_ALLOC=1 arrives via the
 * component define). Exercises the public streaming API end to end with
 * real encode -> decode round trips and API error paths.
 *
 * Output: one "PASS <name>" or "FAIL <name>" line per case, then a final
 * "SUMMARY total=<n> pass=<n> fail=<n>" line. Exit code is 0 only when
 * every case passes.
 */

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "heatshrink_common.h"
#include "heatshrink_decoder.h"
#include "heatshrink_encoder.h"

static int g_total = 0;
static int g_pass = 0;

#define EXPECT(cond)                                                    \
    do {                                                                \
        if (!(cond)) {                                                  \
            printf("\n    assert failed %s:%d: %s\n", __FILE__, __LINE__, #cond); \
            return -1;                                                  \
        }                                                               \
    } while (0)

/* Encode input_size bytes with the streaming encoder API. Returns the
 * compressed size, or -1 on any API error. */
static long hs_encode(heatshrink_encoder *hse, uint8_t *input,
                      size_t input_size, uint8_t *comp, size_t comp_cap) {
    size_t sunk = 0, polled = 0, count = 0;
    uint8_t poll_buf[256];

    while (sunk < input_size) {
        EXPECT(heatshrink_encoder_sink(hse, &input[sunk], input_size - sunk,
                                       &count) == HSER_SINK_OK);
        EXPECT(count > 0);
        sunk += count;
        for (;;) {
            HSE_poll_res pr =
                heatshrink_encoder_poll(hse, poll_buf, sizeof(poll_buf), &count);
            EXPECT(pr == HSER_POLL_EMPTY || pr == HSER_POLL_MORE);
            EXPECT(polled + count <= comp_cap);
            memcpy(&comp[polled], poll_buf, count);
            polled += count;
            if (pr == HSER_POLL_EMPTY) { break; }
        }
    }

    for (;;) {
        HSE_finish_res fr = heatshrink_encoder_finish(hse);
        EXPECT(fr == HSER_FINISH_DONE || fr == HSER_FINISH_MORE);
        if (fr == HSER_FINISH_DONE) { break; }
        for (;;) {
            HSE_poll_res pr =
                heatshrink_encoder_poll(hse, poll_buf, sizeof(poll_buf), &count);
            EXPECT(pr == HSER_POLL_EMPTY || pr == HSER_POLL_MORE);
            EXPECT(polled + count <= comp_cap);
            memcpy(&comp[polled], poll_buf, count);
            polled += count;
            if (pr == HSER_POLL_EMPTY) { break; }
        }
    }
    return (long)polled;
}

/* Decode comp_sz bytes with the streaming decoder API. Returns the
 * decompressed size, or -1 on any API error. */
static long hs_decode(heatshrink_decoder *hsd, uint8_t *comp,
                      size_t comp_sz, uint8_t *out, size_t out_cap) {
    size_t sunk = 0, polled = 0, count = 0;
    uint8_t poll_buf[256];

    while (sunk < comp_sz) {
        HSD_sink_res sr =
            heatshrink_decoder_sink(hsd, &comp[sunk], comp_sz - sunk, &count);
        EXPECT(sr == HSDR_SINK_OK || sr == HSDR_SINK_FULL);
        EXPECT(count > 0);
        sunk += count;
        for (;;) {
            HSD_poll_res pr =
                heatshrink_decoder_poll(hsd, poll_buf, sizeof(poll_buf), &count);
            EXPECT(pr == HSDR_POLL_EMPTY || pr == HSDR_POLL_MORE);
            EXPECT(polled + count <= out_cap);
            memcpy(&out[polled], poll_buf, count);
            polled += count;
            if (pr == HSDR_POLL_EMPTY) { break; }
        }
    }

    for (;;) {
        HSD_finish_res fr = heatshrink_decoder_finish(hsd);
        EXPECT(fr == HSDR_FINISH_DONE || fr == HSDR_FINISH_MORE);
        for (;;) {
            HSD_poll_res pr =
                heatshrink_decoder_poll(hsd, poll_buf, sizeof(poll_buf), &count);
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

/* Round trip helper: returns 0 if decode(encode(input)) == input. */
static int roundtrip(uint8_t window_sz2, uint8_t lookahead_sz2,
                     size_t dec_input_buf, uint8_t *input,
                     size_t input_size) {
    size_t comp_cap = input_size + input_size / 2 + 64;
    size_t out_cap = input_size + 64;
    uint8_t *comp = malloc(comp_cap);
    uint8_t *out = malloc(out_cap);
    if (comp == NULL || out == NULL) { free(comp); free(out); return -1; }
    memset(comp, 0, comp_cap);
    memset(out, 0, out_cap);

    int rc = -1;
    heatshrink_encoder *hse =
        heatshrink_encoder_alloc(window_sz2, lookahead_sz2);
    heatshrink_decoder *hsd =
        heatshrink_decoder_alloc(dec_input_buf, window_sz2, lookahead_sz2);
    if (hse != NULL && hsd != NULL) {
        long comp_sz = hs_encode(hse, input, input_size, comp, comp_cap);
        if (comp_sz >= 0) {
            long out_sz = hs_decode(hsd, comp, (size_t)comp_sz, out, out_cap);
            if (out_sz == (long)input_size &&
                memcmp(input, out, input_size) == 0) {
                rc = 0;
            }
        }
    }
    heatshrink_encoder_free(hse);
    heatshrink_decoder_free(hsd);
    free(comp);
    free(out);
    return rc;
}

static int case_version_macros(void) {
    EXPECT(HEATSHRINK_VERSION_MAJOR == 0);
    EXPECT(HEATSHRINK_VERSION_MINOR == 4);
    EXPECT(HEATSHRINK_VERSION_PATCH == 1);
    EXPECT(HEATSHRINK_MIN_WINDOW_BITS == 4);
    EXPECT(HEATSHRINK_MAX_WINDOW_BITS == 15);
    EXPECT(HEATSHRINK_MIN_LOOKAHEAD_BITS == 3);
    return 0;
}

static int case_alloc_error_paths(void) {
    /* Below/above the documented window range. */
    EXPECT(heatshrink_encoder_alloc(3, 2) == NULL);
    EXPECT(heatshrink_encoder_alloc(16, 4) == NULL);
    /* Lookahead must be >= 3 and < window. */
    EXPECT(heatshrink_encoder_alloc(8, 2) == NULL);
    EXPECT(heatshrink_encoder_alloc(8, 8) == NULL);
    /* Decoder adds: input buffer size must be nonzero. */
    EXPECT(heatshrink_decoder_alloc(0, 8, 4) == NULL);
    EXPECT(heatshrink_decoder_alloc(64, 3, 2) == NULL);
    /* NULL argument error codes. */
    size_t count = 0;
    uint8_t buf[16];
    EXPECT(heatshrink_encoder_sink(NULL, buf, sizeof(buf), &count) ==
           HSER_SINK_ERROR_NULL);
    EXPECT(heatshrink_decoder_sink(NULL, buf, sizeof(buf), &count) ==
           HSDR_SINK_ERROR_NULL);
    return 0;
}

static int case_roundtrip_literal_text(void) {
    /* Highly repetitive ASCII payload, encoded at the CLI's recommended
     * default settings (-w 8 -l 4). */
    const char *chunk = "heatshrink OHOS consumer test; ";
    uint8_t input[31 * 64];
    for (size_t i = 0; i < sizeof(input); i++) {
        input[i] = (uint8_t)chunk[i % strlen(chunk)];
    }
    EXPECT(roundtrip(8, 4, 64, input, sizeof(input)) == 0);
    return 0;
}

static int case_roundtrip_binary_bytes(void) {
    /* All 256 byte values cycling — LRU-hostile binary payload. */
    uint8_t input[4096];
    for (size_t i = 0; i < sizeof(input); i++) {
        input[i] = (uint8_t)(i & 0xFF);
    }
    EXPECT(roundtrip(8, 4, 64, input, sizeof(input)) == 0);
    EXPECT(roundtrip(11, 5, 128, input, sizeof(input)) == 0);
    return 0;
}

static int case_roundtrip_compressible_64k(void) {
    /* Long highly compressible run: verify integrity and that the encoder
     * really compresses it. */
    size_t input_size = 65536;
    uint8_t *input = malloc(input_size);
    EXPECT(input != NULL);
    memset(input, 'A', input_size);
    size_t comp_cap = input_size / 2 + 64;
    uint8_t *comp = malloc(comp_cap);
    uint8_t *out = malloc(input_size + 64);
    EXPECT(comp != NULL && out != NULL);

    heatshrink_encoder *hse = heatshrink_encoder_alloc(8, 4);
    heatshrink_decoder *hsd = heatshrink_decoder_alloc(64, 8, 4);
    EXPECT(hse != NULL && hsd != NULL);
    long comp_sz = hs_encode(hse, input, input_size, comp, comp_cap);
    EXPECT(comp_sz > 0);
    EXPECT((size_t)comp_sz < input_size / 4); /* 'A' * 64k must shrink hard */
    long out_sz = hs_decode(hsd, comp, (size_t)comp_sz, out, input_size + 64);
    EXPECT(out_sz == (long)input_size);
    EXPECT(memcmp(input, out, input_size) == 0);
    heatshrink_encoder_free(hse);
    heatshrink_decoder_free(hsd);
    free(input);
    free(comp);
    free(out);
    return 0;
}

static int case_reset_reuse_deterministic(void) {
    /* Same input through a fresh encoder and through a reset reused one
     * must produce identical compressed bytes. */
    uint8_t input[2048];
    for (size_t i = 0; i < sizeof(input); i++) {
        input[i] = (uint8_t)((i * 31 + (i >> 3)) & 0xFF);
    }
    size_t comp_cap = sizeof(input) + sizeof(input) / 2 + 64;
    uint8_t *a = malloc(comp_cap);
    uint8_t *b = malloc(comp_cap);
    EXPECT(a != NULL && b != NULL);

    heatshrink_encoder *hse = heatshrink_encoder_alloc(9, 5);
    EXPECT(hse != NULL);
    long a_sz = hs_encode(hse, input, sizeof(input), a, comp_cap);
    EXPECT(a_sz > 0);
    heatshrink_encoder_reset(hse);
    long b_sz = hs_encode(hse, input, sizeof(input), b, comp_cap);
    EXPECT(b_sz == a_sz);
    EXPECT(memcmp(a, b, (size_t)a_sz) == 0);
    heatshrink_encoder_free(hse);
    free(a);
    free(b);
    return 0;
}

int main(void) {
    printf("heatshrink %u.%u.%u consumer test (dynamic allocation)\n",
           HEATSHRINK_VERSION_MAJOR, HEATSHRINK_VERSION_MINOR,
           HEATSHRINK_VERSION_PATCH);

    struct {
        const char *name;
        int (*fn)(void);
    } cases[] = {
        {"version_macros", case_version_macros},
        {"alloc_error_paths", case_alloc_error_paths},
        {"roundtrip_literal_text", case_roundtrip_literal_text},
        {"roundtrip_binary_bytes", case_roundtrip_binary_bytes},
        {"roundtrip_compressible_64k", case_roundtrip_compressible_64k},
        {"reset_reuse_deterministic", case_reset_reuse_deterministic},
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
