/*
 * Consumer test for x264 (R34) — real encode through the public API.
 *
 * Verifies the packaged libx264 actually encodes:
 *   1) x264_param_default_preset + x264_encoder_open succeed
 *   2) x264_encoder_headers yields SPS/PPS NAL units
 *   3) x264_encoder_encode turns one I420 frame into NAL units whose
 *      payload starts with the H.264 start code 00 00 00 01
 *   4) negative control: an encoder opened with an invalid bit depth
 *      must fail — otherwise the checks above would be vacuous
 *
 * X264_BUILD is asserted too: the header glues x264_encoder_open to
 * x264_encoder_open_<X264_BUILD>, so a build/lib ABI mismatch is caught
 * at link time.
 */
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include <x264.h>

static int check(int cond, const char *what)
{
    if (!cond) {
        fprintf(stderr, "FAIL: %s\n", what);
        return 1;
    }
    printf("  ok   %s\n", what);
    return 0;
}

static int has_start_code(const uint8_t *p, int len)
{
    return len >= 4 && p[0] == 0x00 && p[1] == 0x00 &&
           p[2] == 0x00 && p[3] == 0x01;
}

int main(void)
{
    int failures = 0;
    x264_t *h = NULL;
    x264_param_t param;
    x264_picture_t pic_in, pic_out;
    x264_nal_t *nal = NULL;
    int i_nal = 0;
    int total_nal = 0;
    int i;
    uint8_t *y;
    int stride;

    printf("x264 consumer checks:\n");

    failures += check(X264_BUILD >= 165,
                      "X264_BUILD >= 165 (header matches packaged lib ABI)");

    /* ---- open the encoder ---- */
    if (x264_param_default_preset(&param, "ultrafast", NULL) < 0) {
        fprintf(stderr, "FAIL: x264_param_default_preset\n");
        return 1;
    }
    param.i_width = 32;
    param.i_height = 32;
    param.i_csp = X264_CSP_I420;
    param.i_log_level = X264_LOG_NONE;

    h = x264_encoder_open(&param);
    failures += check(h != NULL, "x264_encoder_open succeeds");
    if (!h) {
        return 1;
    }

    /* ---- headers (SPS/PPS) ---- */
    if (x264_encoder_headers(h, &nal, &i_nal) < 0) {
        fprintf(stderr, "FAIL: x264_encoder_headers returned < 0\n");
        x264_encoder_close(h);
        return 1;
    }
    failures += check(i_nal > 0, "x264_encoder_headers emits SPS/PPS");

    /* ---- one real frame ---- */
    if (x264_picture_alloc(&pic_in, X264_CSP_I420, param.i_width,
                           param.i_height) < 0) {
        fprintf(stderr, "FAIL: x264_picture_alloc\n");
        x264_encoder_close(h);
        return 1;
    }
    stride = pic_in.img.i_stride[0];
    y = pic_in.img.plane[0];
    for (i = 0; i < param.i_height; i++) {
        memset(y + (size_t)i * stride, 0x80, (size_t)param.i_width);
    }
    memset(pic_in.img.plane[1], 0x80,
           (size_t)pic_in.img.i_stride[1] * (param.i_height / 2));
    memset(pic_in.img.plane[2], 0x80,
           (size_t)pic_in.img.i_stride[2] * (param.i_height / 2));
    pic_in.i_pts = 0;
    pic_in.i_type = X264_TYPE_AUTO;

    if (x264_encoder_encode(h, &nal, &i_nal, &pic_in, &pic_out) < 0) {
        fprintf(stderr, "FAIL: x264_encoder_encode returned < 0\n");
        x264_picture_clean(&pic_in);
        x264_encoder_close(h);
        return 1;
    }
    /* x264 buffers frames (lookahead), so the first call may return none;
     * flush with NULL input until no delayed frames remain. */
    total_nal = i_nal;
    while (x264_encoder_delayed_frames(h) > 0) {
        if (x264_encoder_encode(h, &nal, &i_nal, NULL, &pic_out) < 0) {
            fprintf(stderr, "FAIL: flush encode returned < 0\n");
            x264_picture_clean(&pic_in);
            x264_encoder_close(h);
            return 1;
        }
        total_nal += i_nal;
    }

    failures += check(total_nal > 0,
                      "x264_encoder_encode produces NAL units");
    if (nal != NULL) {
        int found = 0;
        for (i = 0; i < i_nal; i++) {
            if (has_start_code(nal[i].p_payload, nal[i].i_payload)) {
                found = 1;
                break;
            }
        }
        failures += check(found,
                          "NAL payload carries the H.264 start code");
    }

    x264_picture_clean(&pic_in);
    x264_encoder_close(h);

    /* ---- negative control ---- */
    {
        x264_param_t bad;
        x264_t *bad_h;
        x264_param_default_preset(&bad, "ultrafast", NULL);
        bad.i_width = 32;
        bad.i_height = 32;
        bad.i_csp = X264_CSP_I420;
        bad.i_bitdepth = 99;           /* unsupported */
        bad.i_log_level = X264_LOG_NONE;
        bad_h = x264_encoder_open(&bad);
        failures += check(bad_h == NULL,
                          "negative control: invalid bit depth is rejected");
        if (bad_h) {
            x264_encoder_close(bad_h);
        }
    }

    if (failures) {
        printf("\nFAILED: %d check(s)\n", failures);
        return 1;
    }
    printf("\nOK: libx264 encodes a real I420 frame (%d NAL units)\n",
           total_nal);
    return 0;
}
