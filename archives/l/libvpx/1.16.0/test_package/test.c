/* libvpx test_package：真实 VP8 编码一帧并取出码流，非仅版本查询（R34 / R40 多媒体类要求） */
#include <vpx/vpx_codec.h>
#include <vpx/vpx_encoder.h>
#include <vpx/vp8cx.h>

#include <stdio.h>
#include <string.h>

#define W 320
#define H 240

/* 每次 vpx_codec_encode 之后必须立刻取走该次调用产生的包：
   迭代器只覆盖本次调用的输出，不 drain 就进入下一次 encode 会丢掉。 */
static size_t drain(vpx_codec_ctx_t *ctx) {
    vpx_codec_iter_t iter = NULL;
    const vpx_codec_cx_pkt_t *pkt = NULL;
    size_t n = 0;
    while ((pkt = vpx_codec_get_cx_data(ctx, &iter)) != NULL) {
        if (pkt->kind == VPX_CODEC_CX_FRAME_PKT) {
            n += pkt->data.frame.sz;
        }
    }
    return n;
}

int main(void) {
    vpx_codec_iface_t *iface = vpx_codec_vp8_cx();
    if (iface == NULL) {
        fprintf(stderr, "vpx_codec_vp8_cx returned NULL\n");
        return 1;
    }

    vpx_codec_enc_cfg_t cfg;
    if (vpx_codec_enc_config_default(iface, &cfg, 0) != VPX_CODEC_OK) {
        fprintf(stderr, "vpx_codec_enc_config_default failed\n");
        return 1;
    }
    cfg.g_w = W;
    cfg.g_h = H;
    cfg.g_timebase.num = 1;
    cfg.g_timebase.den = 30;
    cfg.rc_target_bitrate = 200;
    /* VP8 默认 g_lag_in_frames=25（alt-ref 前瞻），单帧测试会一直缓冲不出包；置 0 即时输出 */
    cfg.g_lag_in_frames = 0;

    vpx_codec_ctx_t ctx;
    if (vpx_codec_enc_init(&ctx, iface, &cfg, 0) != VPX_CODEC_OK) {
        fprintf(stderr, "vpx_codec_enc_init failed: %s\n", vpx_codec_error(&ctx));
        return 1;
    }

    vpx_image_t img;
    if (vpx_img_alloc(&img, VPX_IMG_FMT_I420, W, H, 1) == NULL) {
        fprintf(stderr, "vpx_img_alloc failed\n");
        vpx_codec_destroy(&ctx);
        return 1;
    }
    /* 造一帧非均匀画面，避免全灰导致码流退化 */
    for (unsigned y = 0; y < img.d_h; y++) {
        memset(img.planes[VPX_PLANE_Y] + y * img.stride[VPX_PLANE_Y],
               (int)(y & 0xFF), img.d_w);
    }
    memset(img.planes[VPX_PLANE_U], 0x80, (img.d_h / 2) * img.stride[VPX_PLANE_U]);
    memset(img.planes[VPX_PLANE_V], 0x40, (img.d_h / 2) * img.stride[VPX_PLANE_V]);

    int rc = 0;
    size_t total = 0;

    if (vpx_codec_encode(&ctx, &img, 0, 1, 0, VPX_DL_GOOD_QUALITY) != VPX_CODEC_OK) {
        fprintf(stderr, "vpx_codec_encode failed: %s\n", vpx_codec_error(&ctx));
        rc = 1;
        goto done;
    }
    total += drain(&ctx);

    /* 送 NULL 冲刷编码器，取走残留的包 */
    if (vpx_codec_encode(&ctx, NULL, 0, 1, 0, VPX_DL_GOOD_QUALITY) != VPX_CODEC_OK) {
        fprintf(stderr, "vpx_codec_encode(flush) failed: %s\n", vpx_codec_error(&ctx));
        rc = 1;
        goto done;
    }
    total += drain(&ctx);

    if (total == 0) {
        fprintf(stderr, "libvpx produced no compressed data\n");
        rc = 1;
        goto done;
    }

    printf("libvpx: version=%s  vp8 encoded %zu bytes from %dx%d  OK\n",
           vpx_codec_version_str(), total, W, H);

done:
    vpx_img_free(&img);
    vpx_codec_destroy(&ctx);
    return rc;
}
