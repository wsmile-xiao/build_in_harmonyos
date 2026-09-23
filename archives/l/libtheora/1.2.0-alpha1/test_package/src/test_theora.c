#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <theora/theoraenc.h>
#include <theora/theoradec.h>

/* Consumer round-trip test (R34): encode 4 frames of 32x32 solid-color
 * YUV420 video with the th_encode_* API, then decode the packets back
 * with th_decode_* and verify frame count, picture dimensions and
 * approximate pixel content survived the roundtrip. */

#define W 32
#define H 32
#define FRAMES 4
#define PLANE_UV ((W / 2) * (H / 2))
#define MAXPKTS 256

static unsigned char yuv_y[FRAMES][W * H];
static unsigned char yuv_u[FRAMES][PLANE_UV];
static unsigned char yuv_v[FRAMES][PLANE_UV];

static ogg_packet pkts[MAXPKTS];
static int npkts = 0;

/* th_encode_flushheader()/th_encode_packetout() hand back buffers that
 * the encoder OWNS and overwrites on the next call (upstream encinfo.c:
 * "we hand the user a buffer which they do not own"), so every packet
 * must be deep-copied immediately (this is what ogg_stream_packetin()
 * does in upstream encoder_example.c). */
static int capture_packet(const ogg_packet *src) {
    unsigned char *copy;
    if (npkts >= MAXPKTS) {
        printf("FAIL: packet overflow\n");
        return 0;
    }
    copy = (unsigned char *)malloc(src->bytes > 0 ? (size_t)src->bytes
                                                  : 1);
    if (!copy) {
        printf("FAIL: out of memory\n");
        return 0;
    }
    if (src->bytes > 0)
        memcpy(copy, src->packet, (size_t)src->bytes);
    pkts[npkts] = *src;
    pkts[npkts].packet = copy;
    npkts++;
    return 1;
}

static long plane_mean(const unsigned char *p, size_t n) {
    unsigned long sum = 0;
    size_t i;
    for (i = 0; i < n; i++)
        sum += p[i];
    return (long)(sum / n);
}

int main(void) {
    const char *ver = th_version_string();
    th_info ti, di;
    th_comment tc, dc;
    th_enc_ctx *enc;
    th_dec_ctx *dec;
    th_setup_info *tsi = NULL;
    int i, r, headers = 0, rem = 1, frames_dec = 0;

    if (!ver) {
        printf("FAIL: th_version_string() == NULL\n");
        return 1;
    }
    printf("th_version_string: %s\n", ver);

    /* ---------------- encode ---------------- */
    th_info_init(&ti);
    ti.frame_width = W;
    ti.frame_height = H;
    ti.pic_width = W;
    ti.pic_height = H;
    ti.pic_x = 0;
    ti.pic_y = 0;
    ti.colorspace = TH_CS_UNSPECIFIED;
    ti.pixel_fmt = TH_PF_420;
    /* th_info_init() leaves fps at 0/0, which the decoder rejects as a
     * corrupt info header (fps_numerator/fps_denominator must be > 0). */
    ti.fps_numerator = 30;
    ti.fps_denominator = 1;
    ti.aspect_numerator = 0;
    ti.aspect_denominator = 0;
    ti.target_bitrate = 0;
    ti.quality = 48;
    ti.keyframe_granule_shift = 6;
    enc = th_encode_alloc(&ti);
    th_info_clear(&ti);
    if (!enc) {
        printf("FAIL: th_encode_alloc()\n");
        return 1;
    }

    th_comment_init(&tc);
    th_comment_add(&tc, "Test=theora-consumer-roundtrip");
    for (;;) {
        ogg_packet op;
        r = th_encode_flushheader(enc, &tc, &op);
        if (r < 0) {
            printf("FAIL: th_encode_flushheader rc=%d\n", r);
            return 1;
        }
        if (r == 0)
            break;
        headers++;
        if (!capture_packet(&op))
            return 1;
    }
    printf("headers: %d\n", headers);
    /* 1.1.x and 1.2.0alpha1 both emit 3 header packets (id/comment/setup);
     * accept the upstream set, the decode side consumes exactly what the
     * encoder produced. */
    if (headers < 3 || headers > 8) {
        printf("FAIL: unexpected header packet count %d\n", headers);
        return 1;
    }

    for (i = 0; i < FRAMES; i++) {
        th_ycbcr_buffer ycbcr;
        memset(yuv_y[i], (unsigned char)(40 + i * 12), sizeof yuv_y[i]);
        memset(yuv_u[i], (unsigned char)(96 + i * 6), sizeof yuv_u[i]);
        memset(yuv_v[i], (unsigned char)(160 - i * 6), sizeof yuv_v[i]);
        ycbcr[0].width = W;
        ycbcr[0].height = H;
        ycbcr[0].stride = W;
        ycbcr[0].data = yuv_y[i];
        ycbcr[1].width = W / 2;
        ycbcr[1].height = H / 2;
        ycbcr[1].stride = W / 2;
        ycbcr[1].data = yuv_u[i];
        ycbcr[2].width = W / 2;
        ycbcr[2].height = H / 2;
        ycbcr[2].stride = W / 2;
        ycbcr[2].data = yuv_v[i];
        r = th_encode_ycbcr_in(enc, ycbcr);
        if (r < 0) {
            printf("FAIL: th_encode_ycbcr_in rc=%d\n", r);
            return 1;
        }
        for (;;) {
            ogg_packet op;
            r = th_encode_packetout(enc, i == FRAMES - 1, &op);
            if (r == 0)
                break;
            if (r < 0) {
                printf("FAIL: th_encode_packetout rc=%d\n", r);
                return 1;
            }
            if (!capture_packet(&op))
                return 1;
        }
    }
    th_encode_free(enc);
    th_comment_clear(&tc);
    printf("packets: %d (%d headers + %d data)\n", npkts, headers,
           npkts - headers);

    /* ---------------- decode ---------------- */
    th_info_init(&di);
    th_comment_init(&dc);
    i = 0;
    rem = 1;
    while (rem > 0) {
        r = th_decode_headerin(&di, &dc, &tsi, &pkts[i]);
        if (r < 0) {
            printf("FAIL: th_decode_headerin rc=%d (packet %d)\n", r, i);
            return 1;
        }
        rem = r;
        /* Only advance past packets that were actually consumed as
         * headers; the call that returns 0 may have been handed the
         * first DATA packet (dump_video.c: advance only when > 0). */
        if (rem > 0)
            i++;
    }
    if (di.pic_width != W || di.pic_height != H) {
        printf("FAIL: decoded pic %dx%d != %dx%d\n", di.pic_width,
               di.pic_height, W, H);
        return 1;
    }
    if (di.pixel_fmt != TH_PF_420) {
        printf("FAIL: decoded pixel_fmt != TH_PF_420\n");
        return 1;
    }
    if (th_comment_query(&dc, "Test", 0) == NULL ||
        strcmp(th_comment_query(&dc, "Test", 0),
               "theora-consumer-roundtrip") != 0) {
        printf("FAIL: comment did not survive the roundtrip\n");
        return 1;
    }

    dec = th_decode_alloc(&di, tsi);
    th_setup_free(tsi);
    if (!dec) {
        printf("FAIL: th_decode_alloc()\n");
        return 1;
    }

    for (; i < npkts; i++) {
        ogg_int64_t gp;
        r = th_decode_packetin(dec, &pkts[i], &gp);
        if (r < 0) {
            printf("FAIL: th_decode_packetin rc=%d (packet %d)\n", r, i);
            return 1;
        }
        if (pkts[i].granulepos >= 0) {
            th_ycbcr_buffer out;
            long my, mu, mv;
            r = th_decode_ycbcr_out(dec, out);
            if (r < 0) {
                printf("FAIL: th_decode_ycbcr_out rc=%d\n", r);
                return 1;
            }
            if (out[0].width != W || out[0].height != H) {
                printf("FAIL: frame %d plane dims %ldx%ld\n", frames_dec,
                       (long)out[0].width, (long)out[0].height);
                return 1;
            }
            my = plane_mean(out[0].data, (size_t)(out[0].height *
                                                  out[0].stride));
            mu = plane_mean(out[1].data, (size_t)(out[1].height *
                                                  out[1].stride));
            mv = plane_mean(out[2].data, (size_t)(out[2].height *
                                                  out[2].stride));
            printf("frame %d means: Y=%ld U=%ld V=%ld (src %d/%d/%d)\n",
                   frames_dec, my, mu, mv, 40 + frames_dec * 12,
                   96 + frames_dec * 6, 160 - frames_dec * 6);
            if (labs(my - (40 + frames_dec * 12)) > 24 ||
                labs(mu - (96 + frames_dec * 6)) > 24 ||
                labs(mv - (160 - frames_dec * 6)) > 24) {
                printf("FAIL: frame %d means drifted too far from source "
                       "(lossy tolerance 24)\n", frames_dec);
                return 1;
            }
            frames_dec++;
        }
    }
    th_decode_free(dec);
    th_info_clear(&di);
    th_comment_clear(&dc);

    if (frames_dec != FRAMES) {
        printf("FAIL: decoded %d frames, expected %d\n", frames_dec,
               FRAMES);
        return 1;
    }
    printf("PASS: %d/%d frames decoded, dims+comment+means verified\n",
           frames_dec, FRAMES);
    return 0;
}
