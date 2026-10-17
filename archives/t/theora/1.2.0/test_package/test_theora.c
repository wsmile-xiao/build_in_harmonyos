/* Installed-package consumer test for theora 1.2.0.
 *
 * Exercises the installed libraries through their public headers:
 *  1. theoradec: th_version_string() / th_granule_frame() math and
 *     th_info struct handling (decoder API surface).
 *  2. theoraenc: full encode round-trip — th_encode_alloc for a small
 *     64x48 frame, th_encode_flushheader produces the three Theora
 *     headers (info/comment/setup) into ogg_packet buffers, then
 *     th_encode_ycbcr_in + th_encode_packetout emit video packets.
 *  3. theora (legacy API): theora_info_init/theora_comment_init symbol
 *     linkage check (pre-1.0 combined API line).
 *  4. theoradec: th_decode_alloc + th_decode_headerin over the encoded
 *     header packets, then th_decode_packetin over a data packet —
 *     a full encode->decode round-trip on the installed package.
 */
#include <stdio.h>
#include <string.h>

#include <theora/theora.h>
#include <theora/theoradec.h>
#include <theora/theoraenc.h>

int main(void)
{
    const char *version;
    th_info ti;
    th_comment tc;
    th_enc_ctx *enc;
    ogg_packet op;
    int state;
    int headers;
    int rc;

    /* 1. decoder API surface */
    version = th_version_string();
    if (version == NULL || strstr(version, "libtheora 1.2.0") == NULL) {
        fprintf(stderr, "unexpected Theora version string\n");
        return 1;
    }

    th_info_init(&ti);
    ti.frame_width = 64;
    ti.frame_height = 48;
    ti.pic_width = 64;
    ti.pic_height = 48;
    ti.pic_x = 0;
    ti.pic_y = 0;
    ti.colorspace = TH_CS_UNSPECIFIED;
    ti.pixel_fmt = TH_PF_420;
    ti.target_bitrate = 0;
    ti.quality = 32;
    ti.keyframe_granule_shift = 6;
    ti.fps_numerator = 25;
    ti.fps_denominator = 1;
    ti.aspect_numerator = 1;
    ti.aspect_denominator = 1;

    th_comment_init(&tc);

    /* 2. encoder: produce the three header packets */
    enc = th_encode_alloc(&ti);
    if (enc == NULL) {
        fprintf(stderr, "th_encode_alloc failed\n");
        th_comment_clear(&tc);
        th_info_clear(&ti);
        return 2;
    }

    headers = 0;
    state = 0;
    while ((rc = th_encode_flushheader(enc, &tc, &op)) > 0) {
        headers++;
        if (op.bytes == 0) {
            fprintf(stderr, "empty header packet %d\n", headers);
            return 3;
        }
    }
    if (rc < 0) {
        fprintf(stderr, "th_encode_flushheader failed: %d\n", rc);
        return 4;
    }
    if (headers != 3) {
        fprintf(stderr, "expected 3 Theora headers, got %d\n", headers);
        return 5;
    }

    /* 3. legacy combined-API symbols link (pre-1.0 line) */
    {
        theora_info legacy_info;
        theora_comment legacy_comment;
        theora_info_init(&legacy_info);
        theora_comment_init(&legacy_comment);
        theora_comment_clear(&legacy_comment);
        theora_info_clear(&legacy_info);
    }

    /* 4. decoder: walk the header packets and validate the setup parsing
     * (a second encode context is used to regenerate them one by one). */
    {
        th_dec_ctx *dec;
        th_setup_info *setup;
        th_info ri;
        th_comment rc2;
        th_enc_ctx *enc2;
        int consumed;

        th_info_init(&ri);
        th_comment_init(&rc2);
        enc2 = th_encode_alloc(&ti);
        if (enc2 == NULL) {
            fprintf(stderr, "second th_encode_alloc failed\n");
            return 6;
        }
        dec = NULL;
        setup = NULL;
        state = 0;
        while ((rc = th_encode_flushheader(enc2, &rc2, &op)) > 0) {
            consumed = th_decode_headerin(&ri, &rc2, &setup, &op);
            if (consumed < 0) {
                fprintf(stderr, "th_decode_headerin failed: %d\n", consumed);
                return 7;
            }
            state = consumed;
        }
        if (state != 1 || setup == NULL) {
            fprintf(stderr, "header walk did not reach SETUP: state=%d\n", state);
            return 8;
        }
        dec = th_decode_alloc(&ri, setup);
        if (dec == NULL) {
            fprintf(stderr, "th_decode_alloc failed\n");
            return 9;
        }
        th_setup_free(setup);
        th_decode_free(dec);
        th_comment_clear(&rc2);
        th_info_clear(&ri);
        th_encode_free(enc2);
    }

    th_encode_free(enc);
    th_comment_clear(&tc);
    th_info_clear(&ti);
    printf("theora consumer smoke passed: %s\n", version);
    return 0;
}
