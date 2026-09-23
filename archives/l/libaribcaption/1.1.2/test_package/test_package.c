/*
 * test_package — libaribcaption 1.1.2 consumer verification (C API).
 *
 * R34: real dependency — decodes the ARIB STD-B24 caption payload the
 * upstream test suite itself uses (sample_data.h, copied verbatim from
 * upstream test/sample_data, MIT (C) magicxqq) through the installed
 * package's public C API, verifies the extracted UTF-8 caption text /
 * plane geometry / DRCS map, and exercises the decoder on malformed
 * inputs (NULL/zero-length, truncated, garbage) to prove it fails safe.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "aribcaption/aribcaption.h"
#include "sample_data.h"

static int g_log_errors = 0;

static void logcat_callback(aribcc_loglevel_t level, const char* message, void* userdata) {
    (void)userdata;
    if (level == ARIBCC_LOGLEVEL_ERROR) {
        g_log_errors++;
        fprintf(stderr, "[aribcc] %s\n", message);
    }
}

static aribcc_decoder_t* make_decoder(aribcc_context_t* ctx) {
    aribcc_decoder_t* decoder = aribcc_decoder_alloc(ctx);
    aribcc_decoder_initialize(decoder,
                              ARIBCC_ENCODING_SCHEME_ARIB_STD_B24_JIS,
                              ARIBCC_CAPTIONTYPE_CAPTION,
                              ARIBCC_PROFILE_A,
                              ARIBCC_LANGUAGEID_FIRST);
    return decoder;
}

/* 1) normal decode: must yield a caption with non-empty UTF-8 text */
static int check_decode_ok(void) {
    aribcc_context_t* ctx = aribcc_context_alloc();
    aribcc_context_set_logcat_callback(ctx, logcat_callback, NULL);
    aribcc_decoder_t* decoder = make_decoder(ctx);

    aribcc_caption_t caption = {0};
    aribcc_decode_status_t st =
        aribcc_decoder_decode(decoder, sample_data_1, sizeof(sample_data_1), 0, &caption);
    printf("[1] decode(sample_data_1) status=%d\n", (int)st);

    int failed = 0;
    if (st != ARIBCC_DECODE_STATUS_GOT_CAPTION) {
        fprintf(stderr, "FAIL: expected GOT_CAPTION, got %d\n", (int)st);
        failed = 1;
    } else if (caption.text == NULL || caption.text[0] == '\0') {
        fprintf(stderr, "FAIL: caption text is empty\n");
        failed = 1;
    } else {
        printf("[1] text=\"%s\"\n", caption.text);
        printf("[1] plane=%dx%d regions=%u lang=%06x\n",
               caption.plane_width, caption.plane_height,
               caption.region_count, caption.iso6392_language_code);
        if (caption.plane_width != 960 && caption.plane_width != 720) {
            fprintf(stderr, "FAIL: unexpected plane width %d\n", caption.plane_width);
            failed = 1;
        }
    }
    aribcc_caption_cleanup(&caption);
    aribcc_decoder_free(decoder);
    aribcc_context_free(ctx);
    return failed;
}

/* 2) DRCS sample: decodes and produces caption + DRCS map */
static int check_decode_drcs(void) {
    aribcc_context_t* ctx = aribcc_context_alloc();
    aribcc_context_set_logcat_callback(ctx, logcat_callback, NULL);
    aribcc_decoder_t* decoder = make_decoder(ctx);

    aribcc_caption_t caption = {0};
    aribcc_decode_status_t st =
        aribcc_decoder_decode(decoder, sample_data_drcs_1, sizeof(sample_data_drcs_1), 0, &caption);
    printf("[2] decode(sample_data_drcs_1) status=%d\n", (int)st);

    int failed = 0;
    if (st != ARIBCC_DECODE_STATUS_GOT_CAPTION) {
        fprintf(stderr, "FAIL: expected GOT_CAPTION for DRCS sample, got %d\n", (int)st);
        failed = 1;
    } else if (caption.drcs_map == NULL) {
        fprintf(stderr, "FAIL: DRCS sample has no drcs_map\n");
        failed = 1;
    } else {
        printf("[2] text=\"%s\" drcs=non-null\n", caption.text ? caption.text : "");
    }
    aribcc_caption_cleanup(&caption);
    aribcc_decoder_free(decoder);
    aribcc_context_free(ctx);
    return failed;
}

/* 3) malformed inputs must not crash and must report no caption */
static int check_malformed_input(void) {
    aribcc_context_t* ctx = aribcc_context_alloc();
    aribcc_context_set_logcat_callback(ctx, logcat_callback, NULL);
    aribcc_decoder_t* decoder = make_decoder(ctx);
    int failed = 0;
    aribcc_caption_t caption = {0};

    /* NULL / zero length — decoder rejects it without crashing */
    aribcc_decode_status_t st = aribcc_decoder_decode(decoder, NULL, 0, 0, &caption);
    printf("[3a] decode(NULL,0) status=%d\n", (int)st);
    if (st == ARIBCC_DECODE_STATUS_GOT_CAPTION) {
        fprintf(stderr, "FAIL: NULL/0 input produced a caption\n");
        failed = 1;
    }

    /* truncated data group (size field claims 0x34c, only header given) */
    static const uint8_t kTruncated[] = {0x80, 0xff, 0xf0, 0x04, 0x00, 0x00, 0x03, 0x4c,
                                         0x3f, 0x00, 0x03, 0x48};
    st = aribcc_decoder_decode(decoder, kTruncated, sizeof(kTruncated), 0, &caption);
    printf("[3b] decode(truncated) status=%d\n", (int)st);
    if (st == ARIBCC_DECODE_STATUS_GOT_CAPTION) {
        fprintf(stderr, "FAIL: truncated input produced a caption\n");
        failed = 1;
    }

    /* garbage bytes */
    static const uint8_t kGarbage[] = {0xde, 0xad, 0xbe, 0xef, 0x00, 0x01,
                                       0x02, 0x03, 0x04, 0x05, 0x06, 0x07};
    st = aribcc_decoder_decode(decoder, kGarbage, sizeof(kGarbage), 0, &caption);
    printf("[3c] decode(garbage) status=%d\n", (int)st);
    if (st == ARIBCC_DECODE_STATUS_GOT_CAPTION) {
        fprintf(stderr, "FAIL: garbage input produced a caption\n");
        failed = 1;
    }

    aribcc_caption_cleanup(&caption);
    aribcc_decoder_free(decoder);
    aribcc_context_free(ctx);
    return failed;
}

int main(void) {
    int failed = 0;
    failed += check_decode_ok();
    failed += check_decode_drcs();
    failed += check_malformed_input();
    printf("test_package: %s (log_errors=%d)\n",
           failed ? "FAILED" : "ALL CHECKS PASSED", g_log_errors);
    return failed ? 1 : 0;
}
