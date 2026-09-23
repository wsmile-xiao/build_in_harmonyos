/* Consumer test for libflac/1.5.0 on OHOS PC.
 *
 * Exercises the delivered libFLAC through a real lossless round trip:
 * encode a deterministic pseudo-random PCM frame stream to a FLAC file
 * with the stream encoder, decode it back with the stream decoder, and
 * require bit-exact recovery.  Uses only the public C API; writes the
 * scratch file under TMPDIR.  Exit code is the verdict.
 */
#include <FLAC/stream_encoder.h>
#include <FLAC/stream_decoder.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define SAMPLES 8192
#define SAMPLE_RATE 44100
#define CHANNELS 2

static FLAC__int32 pcm[SAMPLES * CHANNELS];
static FLAC__int32 decoded[SAMPLES * CHANNELS];
static size_t decoded_len = 0;

static FLAC__StreamDecoderWriteStatus write_cb(
        const FLAC__StreamDecoder *decoder, const FLAC__Frame *frame,
        const FLAC__int32 *const buffer[], void *data) {
    (void)decoder; (void)data;
    /* keep the interleaved L,R order of the source buffer */
    for (unsigned i = 0; i < frame->header.blocksize; ++i) {
        for (unsigned ch = 0; ch < frame->header.channels; ++ch) {
            decoded[decoded_len++] = buffer[ch][i];
        }
    }
    return FLAC__STREAM_DECODER_WRITE_STATUS_CONTINUE;
}

static void error_cb(const FLAC__StreamDecoder *decoder,
                     FLAC__StreamDecoderErrorStatus status, void *data) {
    (void)decoder; (void)data;
    fprintf(stderr, "decoder error: %s\n",
            FLAC__StreamDecoderErrorStatusString[status]);
}

int main(void) {
    int failures = 0;

    /* deterministic pseudo-random signal (xorshift), stereo interleaved */
    unsigned state = 0x1234567u;
    for (size_t i = 0; i < SAMPLES; ++i) {
        state ^= state << 13; state ^= state >> 17; state ^= state << 5;
        pcm[2 * i] = (FLAC__int32)(state % 65536) - 32768;
        pcm[2 * i + 1] = (FLAC__int32)((state >> 8) % 32768) - 16384;
    }

    const char *path = getenv("TMPDIR");
    char flacfile[1024];
    snprintf(flacfile, sizeof(flacfile), "%s/consumer_test.flac",
             path ? path : ".");

    /* ── encode ────────────────────────────────────────────────────── */
    FLAC__StreamEncoder *enc = FLAC__stream_encoder_new();
    if (!enc) { puts("encoder alloc failed"); return 1; }
    FLAC__stream_encoder_set_channels(enc, CHANNELS);
    FLAC__stream_encoder_set_bits_per_sample(enc, 16);
    FLAC__stream_encoder_set_sample_rate(enc, SAMPLE_RATE);
    FLAC__stream_encoder_set_compression_level(enc, 5);
    if (FLAC__stream_encoder_init_file(enc, flacfile, NULL, NULL)
            != FLAC__STREAM_ENCODER_INIT_STATUS_OK) {
        puts("encoder init failed"); return 1;
    }
    if (!FLAC__stream_encoder_process_interleaved(enc, pcm, SAMPLES)) {
        puts("encode process failed"); return 1;
    }
    FLAC__stream_encoder_finish(enc);
    FLAC__stream_encoder_delete(enc);

    /* ── decode ────────────────────────────────────────────────────── */
    FLAC__StreamDecoder *dec = FLAC__stream_decoder_new();
    if (!dec) { puts("decoder alloc failed"); return 1; }
    if (FLAC__stream_decoder_init_file(dec, flacfile, write_cb, NULL,
                                       error_cb, NULL)
            != FLAC__STREAM_DECODER_INIT_STATUS_OK) {
        puts("decoder init failed"); return 1;
    }
    if (!FLAC__stream_decoder_process_until_end_of_stream(dec)) {
        puts("decode failed"); return 1;
    }
    FLAC__stream_decoder_delete(dec);

    /* ── verify bit-exact lossless round trip ──────────────────────── */
    if (decoded_len != SAMPLES * CHANNELS) {
        printf("decoded sample count mismatch: %zu\n", decoded_len);
        ++failures;
    } else if (memcmp(pcm, decoded, sizeof(pcm)) != 0) {
        printf("decoded samples differ from source\n");
        ++failures;
    } else {
        printf("lossless round trip OK: %zu samples bit-exact\n", decoded_len);
    }

    remove(flacfile);
    return failures ? 1 : 0;
}
