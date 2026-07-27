/* ffmpeg test_package：真实编码 + 外部库接线核查，非仅版本查询（R34 / R40 多媒体类要求）
 *
 * 覆盖三件事：
 *   ① 用 libavcodec 真跑一次编码（分配 codec context → open2 → send_frame → receive_packet）
 *   ② 断言本配方接入的外部编码器（openh264 / libvpx / libopus / libmp3lame）在产物中确实可用
 *   ③ 断言 https 协议可用（openssl 接线成功的直接证据）
 */
#include <libavcodec/avcodec.h>
#include <libavformat/avformat.h>
#include <libavutil/avutil.h>
#include <libavutil/frame.h>
#include <libavutil/imgutils.h>
#include <libavfilter/avfilter.h>

#include <stdio.h>
#include <string.h>

#define W 320
#define H 240

/* 用指定编码器真编一帧，返回码流字节数；<=0 表示失败 */
static int encode_one(const char *enc_name) {
    const AVCodec *codec = avcodec_find_encoder_by_name(enc_name);
    if (codec == NULL) {
        fprintf(stderr, "encoder not found: %s\n", enc_name);
        return -1;
    }

    AVCodecContext *ctx = avcodec_alloc_context3(codec);
    if (ctx == NULL) { fprintf(stderr, "alloc_context3 failed: %s\n", enc_name); return -1; }

    ctx->width      = W;
    ctx->height     = H;
    ctx->pix_fmt    = AV_PIX_FMT_YUV420P;
    ctx->time_base  = (AVRational){1, 25};
    ctx->framerate  = (AVRational){25, 1};
    ctx->bit_rate   = 200000;
    ctx->max_b_frames = 0;
    ctx->gop_size   = 1;          /* 首帧即关键帧，单帧测试立刻出包 */

    if (avcodec_open2(ctx, codec, NULL) < 0) {
        fprintf(stderr, "avcodec_open2 failed: %s\n", enc_name);
        avcodec_free_context(&ctx);
        return -1;
    }

    AVFrame *frame = av_frame_alloc();
    frame->format = ctx->pix_fmt;
    frame->width  = W;
    frame->height = H;
    if (av_frame_get_buffer(frame, 0) < 0) {
        fprintf(stderr, "av_frame_get_buffer failed: %s\n", enc_name);
        av_frame_free(&frame);
        avcodec_free_context(&ctx);
        return -1;
    }
    /* 非均匀画面，避免编码器对全灰帧退化 */
    for (int y = 0; y < H; y++) {
        memset(frame->data[0] + y * frame->linesize[0], y & 0xFF, W);
    }
    memset(frame->data[1], 0x80, (H / 2) * frame->linesize[1]);
    memset(frame->data[2], 0x40, (H / 2) * frame->linesize[2]);
    frame->pts = 0;

    int total = 0;
    AVPacket *pkt = av_packet_alloc();
    if (avcodec_send_frame(ctx, frame) >= 0 && avcodec_send_frame(ctx, NULL) >= 0) {
        while (avcodec_receive_packet(ctx, pkt) >= 0) {
            total += pkt->size;
            av_packet_unref(pkt);
        }
    }
    av_packet_free(&pkt);
    av_frame_free(&frame);
    avcodec_free_context(&ctx);
    return total;
}

int main(void) {
    int rc = 0;

    printf("ffmpeg: libavcodec %u.%u.%u  libavformat %u.%u.%u  libavfilter %u.%u.%u\n",
           AV_VERSION_MAJOR(avcodec_version()), AV_VERSION_MINOR(avcodec_version()),
           AV_VERSION_MICRO(avcodec_version()),
           AV_VERSION_MAJOR(avformat_version()), AV_VERSION_MINOR(avformat_version()),
           AV_VERSION_MICRO(avformat_version()),
           AV_VERSION_MAJOR(avfilter_version()), AV_VERSION_MINOR(avfilter_version()),
           AV_VERSION_MICRO(avfilter_version()));

    /* ① 内建编码器真编一帧 */
    int n = encode_one("mpeg4");
    if (n <= 0) { fprintf(stderr, "builtin mpeg4 encode produced %d bytes\n", n); return 1; }
    printf("  builtin mpeg4        : %d bytes  OK\n", n);

    /* ② 本配方接入的外部编码器必须都在（接线失败则 find_encoder_by_name 返回 NULL） */
    const char *ext[] = {"libopenh264", "libvpx", "libopus", "libmp3lame"};
    for (unsigned i = 0; i < sizeof(ext) / sizeof(ext[0]); i++) {
        if (avcodec_find_encoder_by_name(ext[i]) == NULL) {
            fprintf(stderr, "external encoder MISSING: %s\n", ext[i]);
            rc = 1;
        } else {
            printf("  external encoder     : %-12s present\n", ext[i]);
        }
    }
    /* 外部视频编码器同样真编一帧，证明不只是注册了名字 */
    n = encode_one("libopenh264");
    if (n <= 0) { fprintf(stderr, "libopenh264 encode produced %d bytes\n", n); rc = 1; }
    else printf("  libopenh264 encode   : %d bytes  OK\n", n);

    /* ③ https 协议可用 = openssl 接线成功 */
    {
        int found = 0;
        void *opaque = NULL;
        const char *name;
        while ((name = avio_enum_protocols(&opaque, 1)) != NULL) {   /* 1 = output */
            (void)name;
        }
        opaque = NULL;
        while ((name = avio_enum_protocols(&opaque, 0)) != NULL) {   /* 0 = input */
            if (strcmp(name, "https") == 0) { found = 1; break; }
        }
        if (!found) { fprintf(stderr, "protocol MISSING: https (openssl 未接上)\n"); rc = 1; }
        else printf("  protocol             : https present  OK\n");
    }

    /* ④ drawtext 滤镜可用 = freetype/fontconfig 接线成功 */
    if (avfilter_get_by_name("drawtext") == NULL) {
        fprintf(stderr, "filter MISSING: drawtext (freetype/fontconfig 未接上)\n");
        rc = 1;
    } else {
        printf("  filter               : drawtext present  OK\n");
    }

    return rc;
}
