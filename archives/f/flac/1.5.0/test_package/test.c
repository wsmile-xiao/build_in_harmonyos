/* test_flac — Consumer test for flac/1.5.0 conan package (R34: real API round-trip).
 *
 * 1. Generates a deterministic sine/square PCM signal in memory.
 * 2. Encodes it to a FLAC stream via the low-level FLAC__StreamEncoder API
 *    (file-based write callback), exercising stream_encoder/format/metadata.
 * 3. Decodes the resulting FLAC stream via FLAC__StreamDecoder API.
 * 4. Asserts decoded PCM is bit-identical to the source (lossless property).
 * 5. Verifies OGG support is compiled in (FLAC_API_SUPPORTS_OGG_FLAC).
 */
#include <FLAC/format.h>
#include <FLAC/stream_encoder.h>
#include <FLAC/stream_decoder.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define TOTAL_SAMPLES 65536
#define SAMPLE_RATE 44100
#define CHANNELS 2
#define BPS 16

/* decoded output buffer */
static FLAC__int32 *dec_buf[CHANNELS];
static size_t dec_samples = 0;

static FLAC__StreamDecoderWriteStatus dec_write_cb(
        const FLAC__StreamDecoder *dec, const FLAC__Frame *frame,
        const FLAC__int32 *const buffer[], void *client_data)
{
    (void)dec; (void)client_data;
    if (dec_samples + frame->header.blocksize > TOTAL_SAMPLES + 4096)
        return FLAC__STREAM_DECODER_WRITE_STATUS_ABORT;
    for (unsigned c = 0; c < frame->header.channels; c++)
        memcpy(&dec_buf[c][dec_samples], buffer[c], sizeof(FLAC__int32) * frame->header.blocksize);
    dec_samples += frame->header.blocksize;
    return FLAC__STREAM_DECODER_WRITE_STATUS_CONTINUE;
}

static void dec_metadata_cb(const FLAC__StreamDecoder *dec,
        const FLAC__StreamMetadata *meta, void *client_data)
{
    (void)dec; (void)client_data; (void)meta;
}

static void dec_error_cb(const FLAC__StreamDecoder *dec,
        FLAC__StreamDecoderErrorStatus status, void *client_data)
{
    (void)dec; (void)client_data;
    fprintf(stderr, "decoder error: %s\n", FLAC__StreamDecoderErrorStatusString[status]);
}

int main(void)
{
    int failures = 0;

    /* ---- 0. package sanity: version + OGG support ---- */
    printf("FLAC version: %s\n", FLAC__VERSION_STRING);
    if (strcmp(FLAC__VERSION_STRING, "1.5.0") != 0) {
        fprintf(stderr, "FAIL: unexpected version %s\n", FLAC__VERSION_STRING);
        failures++;
    }
    if (!FLAC_API_SUPPORTS_OGG_FLAC) {
        fprintf(stderr, "FAIL: OGG support not compiled in (expected enabled)\n");
        failures++;
    } else {
        printf("OGG support: enabled\n");
    }

    /* ---- 1. generate deterministic PCM ---- */
    FLAC__int32 *pcm[CHANNELS];
    for (int c = 0; c < CHANNELS; c++) {
        pcm[c] = (FLAC__int32 *)malloc(sizeof(FLAC__int32) * TOTAL_SAMPLES);
        dec_buf[c] = (FLAC__int32 *)malloc(sizeof(FLAC__int32) * (TOTAL_SAMPLES + 4096));
        if (!pcm[c] || !dec_buf[c]) { fprintf(stderr, "FAIL: oom\n"); return 1; }
    }
    for (size_t i = 0; i < TOTAL_SAMPLES; i++) {
        /* mix of sine + square for varied compressibility */
        pcm[0][i] = (FLAC__int32)(12000.0 * __builtin_sin(2.0 * 3.14159265358979 * 440.0 * i / SAMPLE_RATE))
                  ^ (i % 16 < 8 ? 0x100 : 0);
        pcm[1][i] = (FLAC__int32)(9000.0 * __builtin_sin(2.0 * 3.14159265358979 * 880.0 * i / SAMPLE_RATE));
    }

    /* ---- 2. encode via FLAC__StreamEncoder ---- */
    FLAC__StreamEncoder *enc = FLAC__stream_encoder_new();
    if (!enc) { fprintf(stderr, "FAIL: encoder new\n"); return 1; }
    if (FLAC__stream_encoder_set_channels(enc, CHANNELS) &&
        FLAC__stream_encoder_set_bits_per_sample(enc, BPS) &&
        FLAC__stream_encoder_set_sample_rate(enc, SAMPLE_RATE) &&
        FLAC__stream_encoder_set_compression_level(enc, 5) &&
        FLAC__stream_encoder_set_total_samples_estimate(enc, TOTAL_SAMPLES)) {
        printf("encoder configured\n");
    } else { fprintf(stderr, "FAIL: encoder config\n"); failures++; }

    const char *flac_path = "roundtrip.flac";
    FLAC__StreamEncoderInitStatus est = FLAC__stream_encoder_init_file(enc, flac_path, NULL, NULL);
    if (est != FLAC__STREAM_ENCODER_INIT_STATUS_OK) {
        fprintf(stderr, "FAIL: encoder init: %s\n", FLAC__StreamEncoderInitStatusString[est]);
        return 1;
    }
    /* build interleaved buffer */
    FLAC__int32 *inter = (FLAC__int32 *)malloc(sizeof(FLAC__int32) * TOTAL_SAMPLES * CHANNELS);
    for (size_t i = 0; i < TOTAL_SAMPLES; i++) {
        inter[i * CHANNELS + 0] = pcm[0][i];
        inter[i * CHANNELS + 1] = pcm[1][i];
    }
    if (!FLAC__stream_encoder_process_interleaved(enc, inter, TOTAL_SAMPLES)) {
        fprintf(stderr, "FAIL: encode process: %s\n",
                FLAC__stream_encoder_get_resolved_state_string(enc));
        failures++;
    }
    if (!FLAC__stream_encoder_finish(enc)) {
        fprintf(stderr, "FAIL: encoder finish\n");
        failures++;
    }
    FLAC__stream_encoder_delete(enc);
    free(inter);
    printf("encoded %s (%zu samples)\n", flac_path, (size_t)TOTAL_SAMPLES);

    /* ---- 3. decode via FLAC__StreamDecoder ---- */
    FLAC__StreamDecoder *decd = FLAC__stream_decoder_new();
    if (!decd) { fprintf(stderr, "FAIL: decoder new\n"); return 1; }
    FLAC__StreamDecoderInitStatus dst = FLAC__stream_decoder_init_file(
        decd, flac_path, dec_write_cb, dec_metadata_cb, dec_error_cb, NULL);
    if (dst != FLAC__STREAM_DECODER_INIT_STATUS_OK) {
        fprintf(stderr, "FAIL: decoder init: %s\n", FLAC__StreamDecoderInitStatusString[dst]);
        return 1;
    }
    if (!FLAC__stream_decoder_process_until_end_of_stream(decd)) {
        fprintf(stderr, "FAIL: decode: %s\n",
                FLAC__stream_decoder_get_resolved_state_string(decd));
        failures++;
    }
    FLAC__stream_decoder_delete(decd);

    /* ---- 4. lossless assertion: decoded == source ---- */
    if (dec_samples != TOTAL_SAMPLES) {
        fprintf(stderr, "FAIL: decoded %zu samples, expected %d\n", dec_samples, TOTAL_SAMPLES);
        failures++;
    } else {
        for (size_t i = 0; i < TOTAL_SAMPLES; i++) {
            for (int c = 0; c < CHANNELS; c++) {
                if (pcm[c][i] != dec_buf[c][i]) {
                    fprintf(stderr, "FAIL: sample %zu ch %d: %d != %d\n",
                            i, c, dec_buf[c][i], pcm[c][i]);
                    failures++;
                    goto done;
                }
            }
        }
        printf("lossless round-trip: %zu samples bit-identical\n", (size_t)TOTAL_SAMPLES);
    }
done:
    for (int c = 0; c < CHANNELS; c++) { free(pcm[c]); free(dec_buf[c]); }

    if (failures == 0) {
        printf("PASS: FLAC__stream_encoder/decoder API round-trip OK\n");
        return 0;
    }
    fprintf(stderr, "FAILED with %d failures\n", failures);
    return 1;
}
