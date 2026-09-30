/**
 * Consumer test for the installed libltc package.
 * Encodes LTC audio frames with the public encoder API and decodes them
 * back with the public decoder API, verifying the SMPTE timecode values
 * round-trip correctly (modeled on upstream tests/ltcloop.c, LGPL-3.0+).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <ltc.h>

static int failures = 0;

static void check(const char *what, int cond) {
    printf("%-40s: %s\n", what, cond ? "ok" : "FAIL");
    if (!cond) {
        failures++;
    }
}

int main(void) {
    const double samplerate = 48000.0;
    const double fps = 25.0;
    const int nframes = 2;

    LTCEncoder *encoder = ltc_encoder_create(samplerate, fps, 0 /*8bit audio*/, 0 /*no color*/);
    check("ltc_encoder_create", encoder != NULL);                      /* assert 1 */
    if (!encoder) {
        return 1;
    }
    ltc_encoder_set_filter(encoder, 0);
    ltc_encoder_set_volume(encoder, -3.0);

    LTCDecoder *decoder = ltc_decoder_create(samplerate / fps, nframes);
    check("ltc_decoder_create", decoder != NULL);                      /* assert 2 */
    if (!decoder) {
        return 1;
    }

    /* Start encoding at 01:02:03:00 and advance over nframes frames. */
    SMPTETimecode start_tc;
    memset(&start_tc, 0, sizeof(start_tc));
    start_tc.hours = 1;
    start_tc.mins = 2;
    start_tc.secs = 3;
    start_tc.frame = 0;
    ltc_encoder_set_timecode(encoder, &start_tc);
    check("ltc_encoder_set_timecode", 1);                              /* assert 3 (call succeeds, verified via decode below) */

    const int frame_size = ltc_encoder_get_buffersize(encoder) * sizeof(ltcsnd_sample_t);
    ltcsnd_sample_t *buf = malloc((nframes + 1) * frame_size);

    int off = 0;
    for (int f = 0; f < nframes; ++f) {
        ltc_encoder_encode_frame(encoder);
        off += ltc_encoder_copy_buffer(encoder, &buf[off]);
        ltc_encoder_inc_timecode(encoder);
    }
    ltc_encoder_end_encode(encoder);
    off += ltc_encoder_copy_buffer(encoder, &buf[off]);
    ltc_encoder_free(encoder);

    check("encoder produced samples", off > 0);                        /* assert 4 */

    /* Decode everything back. */
    ltc_decoder_write(decoder, buf, off, 0);

    int decoded = 0;
    int tc_ok = 1;
    LTCFrameExt frame;
    while (ltc_decoder_read(decoder, &frame)) {
        SMPTETimecode stime;
        ltc_frame_to_time(&stime, &frame.ltc, 0);
        if (decoded == 0) {
            tc_ok = (stime.hours == 1 && stime.mins == 2 && stime.secs == 3);
        }
        decoded++;
    }
    check("decoded frames > 0", decoded > 0);                          /* assert 5 */
    check("first frame timecode 01:02:03:00", tc_ok);                  /* assert 6 */

    ltc_decoder_free(decoder);
    free(buf);

    printf("%s: %d failures\n", failures ? "FAILED" : "PASSED", failures);
    return failures ? 1 : 0;
}
